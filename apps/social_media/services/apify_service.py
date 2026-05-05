"""
Apify REST API wrapper for LinkedIn scraping.

Actors used:
  - simpleapi/linkedin-company-scraper-actor (meZYSFfylaaZzaCNN)
      Input:  {"urls": ["https://www.linkedin.com/company/netflix/"]}
      Output: company info (follower_count, employee_count) + posts array

  - curious_coder/linkedin-jobs-scraper (hKByXkMQaC5Qt9UMN)
      Input:  {"startUrls": [{"url": "<linkedin jobs search URL>"}], "maxItems": 50}
      Output: job listings with title, location, seniority, description, etc.
"""
import time
import logging
import requests
from urllib.parse import urlparse, quote_plus
from django.conf import settings

logger = logging.getLogger(__name__)

APIFY_BASE_URL = "https://api.apify.com/v2"

# Actor IDs — override via settings if you switch actors
COMPANY_ACTOR_ID = getattr(settings, 'APIFY_COMPANY_ACTOR_ID', 'meZYSFfylaaZzaCNN')
JOBS_ACTOR_ID = getattr(settings, 'APIFY_JOBS_ACTOR_ID', 'hKByXkMQaC5Qt9UMN')

# How long to wait (seconds) between status polls
POLL_INTERVAL = 10
# Maximum seconds to wait for an actor run to complete before giving up
RUN_TIMEOUT = 600


class ApifyError(Exception):
    pass


class ApifyService:
    def __init__(self):
        self.token = getattr(settings, 'APIFY_API_TOKEN', '')
        if not self.token:
            raise ApifyError("APIFY_API_TOKEN is not set in environment variables.")

    # ------------------------------------------------------------------
    # Core API helpers
    # ------------------------------------------------------------------

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{APIFY_BASE_URL}/{path}?token={self.token}"
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{APIFY_BASE_URL}/{path}?token={self.token}"
        response = requests.get(url, params=params or {}, timeout=30)
        response.raise_for_status()
        return response.json()

    def _start_run(self, actor_id: str, input_data: dict) -> tuple[str, str]:
        """Start an actor run. Returns (run_id, dataset_id)."""
        data = self._post(f"acts/{actor_id}/runs", input_data)
        run_id = data['data']['id']
        dataset_id = data['data']['defaultDatasetId']
        logger.info(f"[Apify] Started actor {actor_id} — run_id={run_id}")
        return run_id, dataset_id

    def _wait_for_run(self, actor_id: str, run_id: str) -> str:
        """Poll until the run finishes. Returns final status."""
        elapsed = 0
        while elapsed < RUN_TIMEOUT:
            data = self._get(f"acts/{actor_id}/runs/{run_id}")
            status = data['data']['status']
            if status in ('SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT'):
                logger.info(f"[Apify] Run {run_id} finished with status={status}")
                return status
            logger.debug(f"[Apify] Run {run_id} status={status}, waiting {POLL_INTERVAL}s...")
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
        raise ApifyError(f"Actor run {run_id} timed out after {RUN_TIMEOUT}s")

    def _fetch_dataset(self, dataset_id: str) -> list:
        """Fetch all items from a completed run's dataset."""
        url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items?token={self.token}&format=json&clean=true"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()
        # Apify wraps results in {"items": [...]} or returns a plain list
        if isinstance(data, list):
            return data
        return data.get('items', [])

    def _run_actor(self, actor_id: str, input_data: dict) -> list:
        """Full flow: start → wait → fetch results."""
        run_id, dataset_id = self._start_run(actor_id, input_data)
        status = self._wait_for_run(actor_id, run_id)
        if status != 'SUCCEEDED':
            raise ApifyError(f"Actor run ended with status={status}")
        return self._fetch_dataset(dataset_id)

    # ------------------------------------------------------------------
    # LinkedIn-specific scrapers
    # ------------------------------------------------------------------

    def scrape_linkedin_company(self, linkedin_url: str) -> dict:
        """
        Scrape company profile using simpleapi/linkedin-company-scraper-actor.
        Returns a dict with keys: follower_count, employee_count, posts (list).
        """
        logger.info(f"[Apify] Scraping LinkedIn company: {linkedin_url}")
        results = self._run_actor(COMPANY_ACTOR_ID, {"urls": [linkedin_url]})

        if not results:
            logger.warning(f"[Apify] No company data returned for {linkedin_url}")
            return {"follower_count": None, "employee_count": None, "posts": []}

        company = results[0]

        posts_raw = company.get('posts', [])
        posts = []
        for p in posts_raw:
            posts.append({
                "post_id": p.get('urn') or p.get('id') or p.get('url', ''),
                "content": p.get('text') or p.get('content', ''),
                "post_url": p.get('url', ''),
                "posted_at": p.get('postedAtISO') or p.get('postedAt'),
                "author_name": p.get('authorFullName') or p.get('authorName', ''),
                "author_headline": p.get('authorHeadline', ''),
                "num_likes": int(p.get('numLikes') or p.get('likes') or 0),
                "num_comments": int(p.get('numComments') or p.get('comments') or 0),
                "num_shares": int(p.get('numShares') or p.get('shares') or 0),
                "post_type": _infer_post_type(p),
            })

        return {
            "follower_count": _safe_int(company.get('followerCount') or company.get('followers')),
            "employee_count": _safe_int(company.get('employeeCount') or company.get('employees')),
            "posts": posts,
        }

    def scrape_linkedin_jobs(self, competitor_name: str, linkedin_url: str, max_items: int = 50) -> list:
        """
        Scrape job listings using curious_coder/linkedin-jobs-scraper.
        Constructs a LinkedIn Jobs search URL from the company's LinkedIn URL.
        Returns a list of job dicts.
        """
        search_url = _build_jobs_search_url(competitor_name, linkedin_url)
        logger.info(f"[Apify] Scraping LinkedIn jobs for {competitor_name}: {search_url}")

        results = self._run_actor(JOBS_ACTOR_ID, {
            "startUrls": [{"url": search_url}],
            "maxItems": max_items,
        })

        jobs = []
        for j in results:
            # Filter to only jobs actually from this company
            job_company_url = (j.get('companyLinkedinUrl') or '').rstrip('/')
            expected_slug = _extract_slug(linkedin_url)
            if expected_slug and expected_slug not in job_company_url:
                continue

            jobs.append({
                "job_id": str(j.get('id') or j.get('link') or ''),
                "title": j.get('title', ''),
                "location": j.get('location', ''),
                "employment_type": j.get('employmentType', ''),
                "seniority_level": j.get('seniorityLevel', ''),
                "job_function": j.get('jobFunction', ''),
                "industries": j.get('industries', ''),
                "description": j.get('descriptionText') or j.get('description', ''),
                "job_url": j.get('link') or j.get('url', ''),
                "apply_url": j.get('applyUrl', ''),
                "posted_at": j.get('postedAt'),
            })

        logger.info(f"[Apify] Found {len(jobs)} jobs for {competitor_name}")
        return jobs


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _infer_post_type(post: dict) -> str:
    t = (post.get('type') or '').lower()
    if 'article' in t:
        return 'article'
    if 'job' in t:
        return 'job'
    return 'post'


def _extract_slug(linkedin_url: str) -> str:
    """Extract company slug from https://www.linkedin.com/company/netflix/ → 'netflix'"""
    try:
        parts = urlparse(linkedin_url).path.strip('/').split('/')
        if 'company' in parts:
            idx = parts.index('company')
            return parts[idx + 1] if idx + 1 < len(parts) else ''
    except Exception:
        pass
    return ''


def _build_jobs_search_url(company_name: str, linkedin_url: str) -> str:
    """
    Build a LinkedIn Jobs search URL for a given company.
    Uses the company slug from the LinkedIn URL as the keyword so results
    are scoped to that company. We then filter by companyLinkedinUrl post-scrape.
    """
    slug = _extract_slug(linkedin_url)
    keyword = slug if slug else company_name
    # f_TPR=r604800 = "posted in last 7 days"
    return f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keyword)}&f_TPR=r604800"
