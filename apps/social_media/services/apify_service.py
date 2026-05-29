"""
Apify REST API wrapper for LinkedIn scraping.

Actors used:
  - automation-lab/linkedin-company-scraper (automation-lab~linkedin-company-scraper)
      Input:  {"companyUrls": ["https://www.linkedin.com/company/netflix/"], "maxCompanies": 1}
      Output: followerCount, employeeCount, name, industry, etc. (no posts)

  - valig/linkedin-jobs-scraper (valig~linkedin-jobs-scraper)
      Input:  {"companyName": ["Honda"], "datePosted": "r604800", "limit": 50}
      Output: id, url, title, location, companyName, companyUrl, description, contractType,
              experienceLevel, postedDate

  - harvestapi/linkedin-profile-posts (harvestapi~linkedin-profile-posts)
      Input:  {"targetUrls": ["https://www.linkedin.com/company/netflix/"],
               "postedLimitDate": "2026-05-29", "maxPosts": 50}
      Output: id, content, linkedinUrl, postedAt, engagement{likes,comments,shares},
              author{name, info}
"""
import time
import logging
import requests
from datetime import date
from urllib.parse import urlparse
from django.conf import settings

logger = logging.getLogger(__name__)

APIFY_BASE_URL = "https://api.apify.com/v2"

# Actor IDs — override via settings if you switch actors
COMPANY_ACTOR_ID = getattr(settings, 'APIFY_COMPANY_ACTOR_ID', 'automation-lab~linkedin-company-scraper')
JOBS_ACTOR_ID = getattr(settings, 'APIFY_JOBS_ACTOR_ID', 'valig~linkedin-jobs-scraper')
POSTS_ACTOR_ID = getattr(settings, 'APIFY_POSTS_ACTOR_ID', 'harvestapi~linkedin-profile-posts')

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
        Scrape company profile using automation-lab/linkedin-company-scraper.
        Returns a dict with keys: follower_count, employee_count, posts (always empty).
        Posts are not supported by this actor — handled separately in future.
        """
        logger.info(f"[Apify] Scraping LinkedIn company: {linkedin_url}")
        results = self._run_actor(COMPANY_ACTOR_ID, {
            "companyUrls": [linkedin_url],
            "maxCompanies": 1,
        })

        if not results:
            logger.warning(f"[Apify] No company data returned for {linkedin_url}")
            return {"follower_count": None, "employee_count": None, "posts": []}

        company = results[0]

        return {
            "follower_count": _safe_int(company.get('followerCount')),
            "employee_count": _safe_int(company.get('employeeCount')),
            "posts": [],  # Posts not supported by this actor
        }

    def scrape_linkedin_jobs(self, competitor_name: str, linkedin_url: str, max_items: int = 50) -> list:
        """
        Scrape job listings using valig/linkedin-jobs-scraper.
        Searches by company name and filters to last 7 days.
        Returns a list of job dicts.
        """
        logger.info(f"[Apify] Scraping LinkedIn jobs for {competitor_name}")

        results = self._run_actor(JOBS_ACTOR_ID, {
            "companyName": [competitor_name],
            "datePosted": "r604800",  # last 7 days
            "limit": max_items,
        })

        expected_slug = _extract_slug(linkedin_url)
        jobs = []
        for j in results:
            # Filter to only jobs from this specific company
            job_company_url = (j.get('companyUrl') or '').rstrip('/')
            if expected_slug and expected_slug not in job_company_url:
                continue

            jobs.append({
                "job_id": str(j.get('id') or j.get('url') or ''),
                "title": j.get('title', ''),
                "location": j.get('location', ''),
                "employment_type": j.get('contractType', ''),
                "seniority_level": j.get('experienceLevel', ''),
                "job_function": '',
                "industries": '',
                "description": j.get('description') or j.get('descriptionHtml', ''),
                "job_url": j.get('url', ''),
                "apply_url": j.get('url', ''),
                "posted_at": j.get('postedDate'),
            })

        logger.info(f"[Apify] Found {len(jobs)} jobs for {competitor_name}")
        return jobs

    def scrape_linkedin_posts(self, linkedin_url: str, posts_since: date, max_posts: int = 50) -> list:
        """
        Scrape company posts using harvestapi/linkedin-profile-posts.
        Only fetches posts on or after posts_since date — keeps costs low.
        Returns a list of post dicts.
        """
        logger.info(f"[Apify] Scraping LinkedIn posts for {linkedin_url} since {posts_since}")

        results = self._run_actor(POSTS_ACTOR_ID, {
            "targetUrls": [linkedin_url],
            "postedLimitDate": posts_since.strftime('%Y-%m-%d'),
            "maxPosts": max_posts,
            "scrapeReactions": False,
            "scrapeComments": False,
        })

        posts = []
        for p in results:
            engagement = p.get('engagement') or {}
            author = p.get('author') or {}

            # postedAt is an object: {timestamp: ..., date: "..."}
            posted_at_raw = p.get('postedAt')
            if isinstance(posted_at_raw, dict):
                posted_at = posted_at_raw.get('timestamp') or posted_at_raw.get('date')
            else:
                posted_at = posted_at_raw

            posts.append({
                "post_id": str(p.get('id') or p.get('linkedinUrl') or ''),
                "content": p.get('content', ''),
                "post_url": p.get('linkedinUrl', ''),
                "posted_at": posted_at,
                "author_name": author.get('name', ''),
                "author_headline": author.get('info', ''),
                "num_likes": int(engagement.get('likes') or 0),
                "num_comments": int(engagement.get('comments') or 0),
                "num_shares": int(engagement.get('shares') or 0),
                "post_type": "post",
            })

        logger.info(f"[Apify] Found {len(posts)} posts for {linkedin_url}")
        return posts


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
