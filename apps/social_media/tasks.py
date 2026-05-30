"""
Celery tasks for LinkedIn social media scraping.
Runs separately from the website scraping pipeline.
"""
import logging
from datetime import date, datetime, timedelta, timezone

from celery import shared_task
from django.utils import timezone as dj_timezone

logger = logging.getLogger(__name__)


@shared_task
def run_linkedin_monitoring():
    """
    Daily task: scrape LinkedIn for every competitor that has a linkedin_url.
    Registered in celery.py to run at 3 AM daily (1 hour after website scraping).
    """
    from apps.monitoring.models import Competitor

    competitors = (
        Competitor.objects
        .filter(is_deleted=False)
        .exclude(linkedin_url__isnull=True)
        .exclude(linkedin_url='')
    )

    if not competitors.exists():
        logger.info("[LinkedIn] No competitors with a LinkedIn URL — skipping.")
        return {"status": "skipped", "message": "No competitors have a LinkedIn URL"}

    results = {}
    for comp in competitors:
        logger.info(f"[LinkedIn] ══ Starting for {comp.name} ══")
        try:
            result = _scrape_competitor_linkedin(comp)
            results[comp.name] = result
        except Exception as e:
            logger.error(f"[LinkedIn] Failed for {comp.name}: {e}")
            results[comp.name] = {"status": "error", "error": str(e)}

    logger.info(f"[LinkedIn] Finished all: {list(results.keys())}")

    # Send email alerts to opted-in users
    try:
        from apps.accounts.email_service import send_job_alerts, send_follower_change_alerts
        send_job_alerts()
        send_follower_change_alerts()
    except Exception as exc:
        logger.error(f"[LinkedIn] Email alert dispatch failed: {exc}")

    return results


@shared_task
def scrape_linkedin_for_competitor(competitor_id: int):
    """
    Scrape LinkedIn for a single competitor by ID.
    Call this manually via management command or API for targeted runs.
    """
    from apps.monitoring.models import Competitor

    try:
        comp = Competitor.objects.get(id=competitor_id, is_deleted=False)
    except Competitor.DoesNotExist:
        logger.error(f"[LinkedIn] Competitor id={competitor_id} not found.")
        return {"status": "error", "error": "Competitor not found"}

    return _scrape_competitor_linkedin(comp)


@shared_task
def run_facebook_monitoring():
    """Daily task: scrape Facebook for every competitor that has a facebook_url."""
    from apps.monitoring.models import Competitor

    competitors = (
        Competitor.objects
        .filter(is_deleted=False)
        .exclude(facebook_url__isnull=True)
        .exclude(facebook_url='')
    )

    if not competitors.exists():
        logger.info("[Facebook] No competitors with a Facebook URL — skipping.")
        return {"status": "skipped"}

    results = {}
    for comp in competitors:
        logger.info(f"[Facebook] ══ Starting for {comp.name} ══")
        try:
            results[comp.name] = _scrape_competitor_facebook(comp)
        except Exception as e:
            logger.error(f"[Facebook] Failed for {comp.name}: {e}")
            results[comp.name] = {"status": "error", "error": str(e)}

    return results


@shared_task
def scrape_facebook_for_competitor(competitor_id: int):
    """Scrape Facebook for a single competitor by ID."""
    from apps.monitoring.models import Competitor

    try:
        comp = Competitor.objects.get(id=competitor_id, is_deleted=False)
    except Competitor.DoesNotExist:
        return {"status": "error", "error": "Competitor not found"}

    return _scrape_competitor_facebook(comp)


@shared_task
def run_instagram_monitoring():
    """Daily task: scrape Instagram for every competitor that has an instagram_url."""
    from apps.monitoring.models import Competitor

    competitors = (
        Competitor.objects
        .filter(is_deleted=False)
        .exclude(instagram_url__isnull=True)
        .exclude(instagram_url='')
    )

    if not competitors.exists():
        logger.info("[Instagram] No competitors with an Instagram URL — skipping.")
        return {"status": "skipped"}

    results = {}
    for comp in competitors:
        logger.info(f"[Instagram] ══ Starting for {comp.name} ══")
        try:
            results[comp.name] = _scrape_competitor_instagram(comp)
        except Exception as e:
            logger.error(f"[Instagram] Failed for {comp.name}: {e}")
            results[comp.name] = {"status": "error", "error": str(e)}

    return results


@shared_task
def scrape_instagram_for_competitor(competitor_id: int):
    """Scrape Instagram for a single competitor by ID."""
    from apps.monitoring.models import Competitor

    try:
        comp = Competitor.objects.get(id=competitor_id, is_deleted=False)
    except Competitor.DoesNotExist:
        return {"status": "error", "error": "Competitor not found"}

    return _scrape_competitor_instagram(comp)


# ------------------------------------------------------------------
# Internal logic (not Celery tasks)
# ------------------------------------------------------------------

def _scrape_competitor_linkedin(competitor, posts_since_override=None) -> dict:
    """Run the full LinkedIn scrape (company data + posts + jobs) for one competitor."""
    from apps.social_media.services.apify_service import ApifyService, ApifyError

    if not competitor.linkedin_url:
        return {"status": "skipped", "reason": "No LinkedIn URL"}

    try:
        service = ApifyService()
    except ApifyError as e:
        logger.error(f"[LinkedIn] Apify init failed: {e}")
        return {"status": "error", "error": str(e)}

    result = {}

    # --- Company snapshot (followers + employees) ---
    try:
        company_data = service.scrape_linkedin_company(competitor.linkedin_url)
        snapshot_saved = _save_snapshot(
            competitor,
            company_data['follower_count'],
            company_data['employee_count'],
        )
        result['snapshot'] = snapshot_saved
    except Exception as e:
        logger.error(f"[LinkedIn] Company scrape failed for {competitor.name}: {e}")
        result['snapshot'] = {"error": str(e)}

    # --- Posts (date-bounded to avoid scraping full history) ---
    try:
        from apps.social_media.models import SocialMediaPost
        if posts_since_override is not None:
            posts_since = posts_since_override
        else:
            # Always scrape last 5 days — covers both new post discovery and
            # engagement refresh (likes/comments/shares) on recent posts.
            posts_since = date.today() - timedelta(days=5)
        posts_raw = service.scrape_linkedin_posts(competitor.linkedin_url, posts_since)
        posts_saved = _save_posts(competitor, posts_raw)
        result['posts'] = {
            "saved": posts_saved['created'],
            "updated": posts_saved['updated'],
            "total": len(posts_raw),
            "since": str(posts_since),
        }
    except Exception as e:
        logger.error(f"[LinkedIn] Posts scrape failed for {competitor.name}: {e}")
        result['posts'] = {"error": str(e)}

    # --- Job listings ---
    try:
        jobs_raw = service.scrape_linkedin_jobs(competitor.name, competitor.linkedin_url)
        jobs_result = _save_jobs(competitor, jobs_raw)
        result['jobs'] = jobs_result
    except Exception as e:
        logger.error(f"[LinkedIn] Jobs scrape failed for {competitor.name}: {e}")
        result['jobs'] = {"error": str(e)}

    result['status'] = 'success'
    return result


def _save_posts(competitor, posts: list, platform: str = 'linkedin') -> dict:
    """
    Upsert posts in DB.
    - New posts: created.
    - Existing posts: engagement numbers (likes/comments/shares) refreshed.
    Returns counts of created and updated posts.
    """
    from apps.social_media.models import SocialMediaPost

    created_count = 0
    updated_count = 0

    for p in posts:
        post_id = p.get('post_id', '').strip()
        if not post_id:
            continue

        posted_at = _parse_dt(p.get('posted_at'))

        obj, created = SocialMediaPost.objects.get_or_create(
            competitor=competitor,
            platform=platform,
            post_id=post_id,
            defaults={
                'content': p.get('content', ''),
                'post_type': p.get('post_type', 'post'),
                'post_url': p.get('post_url') or None,
                'posted_at': posted_at,
                'author_name': p.get('author_name', ''),
                'author_headline': p.get('author_headline', ''),
                'num_likes': p.get('num_likes', 0),
                'num_comments': p.get('num_comments', 0),
                'num_shares': p.get('num_shares', 0),
            },
        )
        if created:
            created_count += 1
        else:
            obj.num_likes = p.get('num_likes', 0)
            obj.num_comments = p.get('num_comments', 0)
            obj.num_shares = p.get('num_shares', 0)
            obj.save(update_fields=['num_likes', 'num_comments', 'num_shares'])
            updated_count += 1

    logger.info(
        f"[{platform.capitalize()}] {competitor.name}: {created_count} new posts, {updated_count} engagement refreshed"
    )
    return {"created": created_count, "updated": updated_count}


def _save_jobs(competitor, jobs: list) -> dict:
    """
    Upsert job listings.
    - New jobs: created with is_new=True
    - Existing jobs: updated last_seen_at, is_active=True, is_new=False
    - Jobs not in this scrape: marked is_active=False
    Returns a summary dict.
    """
    from apps.social_media.models import JobPosting

    scraped_ids = set()
    new_count = 0
    updated_count = 0

    for j in jobs:
        job_id = str(j.get('job_id', '')).strip()
        if not job_id:
            continue

        scraped_ids.add(job_id)
        posted_at = _parse_dt(j.get('posted_at'))

        existing = JobPosting.objects.filter(competitor=competitor, job_id=job_id).first()
        if existing:
            existing.is_active = True
            existing.is_new = False
            existing.last_seen_at = dj_timezone.now()
            existing.save(update_fields=['is_active', 'is_new', 'last_seen_at'])
            updated_count += 1
        else:
            JobPosting.objects.create(
                competitor=competitor,
                job_id=job_id,
                title=j.get('title', ''),
                location=j.get('location', ''),
                employment_type=j.get('employment_type', ''),
                seniority_level=j.get('seniority_level', ''),
                job_function=j.get('job_function', ''),
                industries=j.get('industries', ''),
                description=j.get('description', ''),
                job_url=j.get('job_url') or None,
                apply_url=j.get('apply_url') or None,
                posted_at=posted_at,
                is_new=True,
                is_active=True,
            )
            new_count += 1

    # Mark jobs that disappeared as inactive
    deactivated = (
        JobPosting.objects
        .filter(competitor=competitor, is_active=True)
        .exclude(job_id__in=scraped_ids)
        .update(is_active=False)
    )

    logger.info(
        f"[LinkedIn] {competitor.name} jobs — new={new_count}, updated={updated_count}, deactivated={deactivated}"
    )
    return {"new": new_count, "updated": updated_count, "deactivated": deactivated}


def _save_snapshot(competitor, follower_count, employee_count, platform: str = 'linkedin') -> dict:
    """Record a daily follower/employee count snapshot."""
    from apps.social_media.models import SocialMediaSnapshot

    if follower_count is None and employee_count is None:
        return {"saved": False, "reason": "No count data returned"}

    SocialMediaSnapshot.objects.create(
        competitor=competitor,
        platform=platform,
        follower_count=follower_count,
        employee_count=employee_count,
    )
    logger.info(
        f"[{platform.capitalize()}] {competitor.name} snapshot — followers={follower_count}, employees={employee_count}"
    )
    return {"saved": True, "follower_count": follower_count, "employee_count": employee_count}


def _scrape_competitor_facebook(competitor, posts_since_override=None) -> dict:
    """Run the full Facebook scrape (page snapshot + posts) for one competitor."""
    from apps.social_media.services.apify_service import ApifyService, ApifyError

    if not competitor.facebook_url:
        return {"status": "skipped", "reason": "No Facebook URL"}

    try:
        service = ApifyService()
    except ApifyError as e:
        logger.error(f"[Facebook] Apify init failed: {e}")
        return {"status": "error", "error": str(e)}

    result = {}

    # --- Page snapshot (followers) ---
    try:
        page_data = service.scrape_facebook_page(competitor.facebook_url)
        snapshot_saved = _save_snapshot(competitor, page_data['follower_count'], None, platform='facebook')
        result['snapshot'] = snapshot_saved
    except Exception as e:
        logger.error(f"[Facebook] Page scrape failed for {competitor.name}: {e}")
        result['snapshot'] = {"error": str(e)}

    # --- Posts (last 5 days — new posts + engagement refresh) ---
    try:
        posts_since = posts_since_override or (date.today() - timedelta(days=5))
        posts_raw = service.scrape_facebook_posts(competitor.facebook_url, posts_since)
        posts_saved = _save_posts(competitor, posts_raw, platform='facebook')
        result['posts'] = {
            "saved": posts_saved['created'],
            "updated": posts_saved['updated'],
            "total": len(posts_raw),
            "since": str(posts_since),
        }
    except Exception as e:
        logger.error(f"[Facebook] Posts scrape failed for {competitor.name}: {e}")
        result['posts'] = {"error": str(e)}

    result['status'] = 'success'
    return result


def _scrape_competitor_instagram(competitor, posts_since_override=None) -> dict:
    """Run the full Instagram scrape (profile snapshot + posts) for one competitor."""
    from apps.social_media.services.apify_service import ApifyService, ApifyError

    if not competitor.instagram_url:
        return {"status": "skipped", "reason": "No Instagram URL"}

    try:
        service = ApifyService()
    except ApifyError as e:
        logger.error(f"[Instagram] Apify init failed: {e}")
        return {"status": "error", "error": str(e)}

    result = {}

    # --- Profile snapshot (followers) ---
    try:
        profile_data = service.scrape_instagram_profile(competitor.instagram_url)
        snapshot_saved = _save_snapshot(competitor, profile_data['follower_count'], None, platform='instagram')
        result['snapshot'] = snapshot_saved
    except Exception as e:
        logger.error(f"[Instagram] Profile scrape failed for {competitor.name}: {e}")
        result['snapshot'] = {"error": str(e)}

    # --- Posts (last 5 days — new posts + engagement refresh) ---
    try:
        posts_since = posts_since_override or (date.today() - timedelta(days=5))
        posts_raw = service.scrape_instagram_posts(competitor.instagram_url, posts_since)
        posts_saved = _save_posts(competitor, posts_raw, platform='instagram')
        result['posts'] = {
            "saved": posts_saved['created'],
            "updated": posts_saved['updated'],
            "total": len(posts_raw),
            "since": str(posts_since),
        }
    except Exception as e:
        logger.error(f"[Instagram] Posts scrape failed for {competitor.name}: {e}")
        result['posts'] = {"error": str(e)}

    result['status'] = 'success'
    return result


def _parse_dt(value) -> datetime | None:
    """Best-effort parse of a datetime string or timestamp into an aware datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        for fmt in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d'):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None
