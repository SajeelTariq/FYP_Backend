"""
Management command to manually trigger social media scraping without Celery/cron.

Usage:
    # Scrape all platforms for all competitors
    python manage.py run_linkedin_scraping

    # Scrape a specific platform only
    python manage.py run_linkedin_scraping --platform facebook
    python manage.py run_linkedin_scraping --platform instagram
    python manage.py run_linkedin_scraping --platform linkedin

    # Scrape a single competitor by ID
    python manage.py run_linkedin_scraping --competitor-id 3 --platform linkedin

    # Dry run: show what would be scraped without calling Apify
    python manage.py run_linkedin_scraping --dry-run

    # Override posts lookback window
    python manage.py run_linkedin_scraping --days-back 7
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.monitoring.models import Competitor
from apps.social_media.tasks import (
    _scrape_competitor_linkedin,
    _scrape_competitor_facebook,
    _scrape_competitor_instagram,
)

PLATFORM_URL_FIELD = {
    'linkedin': 'linkedin_url',
    'facebook': 'facebook_url',
    'instagram': 'instagram_url',
}

SCRAPE_FN = {
    'linkedin': _scrape_competitor_linkedin,
    'facebook': _scrape_competitor_facebook,
    'instagram': _scrape_competitor_instagram,
}


class Command(BaseCommand):
    help = "Manually run social media scraping for competitors (bypasses Celery queue)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--platform',
            choices=['linkedin', 'facebook', 'instagram', 'all'],
            default='all',
            help='Which platform to scrape (default: all).',
        )
        parser.add_argument(
            '--competitor-id',
            type=int,
            default=None,
            help='Scrape a single competitor by ID. Omit to scrape all.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print which competitors would be scraped without calling Apify.',
        )
        parser.add_argument(
            '--days-back',
            type=int,
            default=None,
            help='Force posts_since to N days ago. Overrides the default 5-day window.',
        )

    def handle(self, *args, **options):
        platform = options.get('platform')
        competitor_id = options.get('competitor_id')
        dry_run = options.get('dry_run')
        days_back = options.get('days_back')

        platforms = ['linkedin', 'facebook', 'instagram'] if platform == 'all' else [platform]
        force_posts_since = date.today() - timedelta(days=days_back) if days_back is not None else None

        if force_posts_since:
            self.stdout.write(self.style.WARNING(f"Overriding posts_since → {force_posts_since}"))

        for plat in platforms:
            self.stdout.write(self.style.HTTP_INFO(f"\n══ Platform: {plat.upper()} ══"))
            url_field = PLATFORM_URL_FIELD[plat]

            if competitor_id:
                try:
                    comp = Competitor.objects.get(id=competitor_id, is_deleted=False)
                    competitors = [comp]
                except Competitor.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"Competitor id={competitor_id} not found."))
                    continue
            else:
                competitors = list(
                    Competitor.objects
                    .filter(is_deleted=False)
                    .exclude(**{f"{url_field}__isnull": True})
                    .exclude(**{url_field: ''})
                )

            if not competitors:
                self.stdout.write(self.style.WARNING(f"No competitors with a {plat} URL — skipping."))
                continue

            self.stdout.write(f"Found {len(competitors)} competitor(s):")
            for c in competitors:
                self.stdout.write(f"  [{c.id}] {c.name} — {getattr(c, url_field)}")

            if dry_run:
                continue

            scrape_fn = SCRAPE_FN[plat]
            for comp in competitors:
                self.stdout.write(f"\n→ Scraping {comp.name}...")
                try:
                    result = scrape_fn(comp, posts_since_override=force_posts_since)
                    posts = result.get('posts', {})
                    snapshot = result.get('snapshot', {})

                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ Posts:    {posts.get('saved', '?')} new, "
                        f"{posts.get('updated', '?')} engagement refreshed / {posts.get('total', '?')} total"
                    ))
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ Snapshot: followers={snapshot.get('follower_count')}"
                    ))

                    if plat == 'linkedin':
                        jobs = result.get('jobs', {})
                        self.stdout.write(self.style.SUCCESS(
                            f"  ✓ Jobs:     {jobs.get('new', '?')} new, "
                            f"{jobs.get('updated', '?')} updated, "
                            f"{jobs.get('deactivated', '?')} deactivated"
                        ))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"  ✗ Error: {e}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN — no Apify calls made."))

        self.stdout.write(self.style.SUCCESS("\nDone."))
