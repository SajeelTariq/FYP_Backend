"""
Management command to manually trigger LinkedIn scraping without Celery/cron.

Usage:
    # Scrape all competitors that have a LinkedIn URL
    python manage.py run_linkedin_scraping

    # Scrape a single competitor by ID
    python manage.py run_linkedin_scraping --competitor-id 3

    # Dry run: show what would be scraped without calling Apify
    python manage.py run_linkedin_scraping --dry-run
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.monitoring.models import Competitor
from apps.social_media.tasks import _scrape_competitor_linkedin


class Command(BaseCommand):
    help = "Manually run LinkedIn scraping for competitors (bypasses Celery queue)"

    def add_arguments(self, parser):
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
            help='Force posts_since to N days ago (e.g. --days-back 1 for yesterday). Overrides the auto date logic.',
        )

    def handle(self, *args, **options):
        competitor_id = options.get('competitor_id')
        dry_run = options.get('dry_run')
        days_back = options.get('days_back')

        if competitor_id:
            try:
                competitors = [Competitor.objects.get(id=competitor_id, is_deleted=False)]
            except Competitor.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Competitor id={competitor_id} not found."))
                return
        else:
            competitors = list(
                Competitor.objects
                .filter(is_deleted=False)
                .exclude(linkedin_url__isnull=True)
                .exclude(linkedin_url='')
            )

        if not competitors:
            self.stdout.write(self.style.WARNING("No competitors with a LinkedIn URL found."))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {len(competitors)} competitor(s) to scrape:"))
        for c in competitors:
            self.stdout.write(f"  [{c.id}] {c.name} — {c.linkedin_url}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no Apify calls made."))
            return

        force_posts_since = date.today() - timedelta(days=days_back) if days_back is not None else None
        if force_posts_since:
            self.stdout.write(self.style.WARNING(f"Overriding posts_since → {force_posts_since}"))

        for comp in competitors:
            self.stdout.write(f"\n→ Scraping {comp.name}...")
            try:
                result = _scrape_competitor_linkedin(comp, posts_since_override=force_posts_since)
                posts = result.get('posts', {})
                jobs = result.get('jobs', {})
                snapshot = result.get('snapshot', {})

                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Posts:    {posts.get('saved', '?')} new / {posts.get('total', '?')} total"
                ))
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Jobs:     {jobs.get('new', '?')} new, "
                    f"{jobs.get('updated', '?')} updated, "
                    f"{jobs.get('deactivated', '?')} deactivated"
                ))
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Snapshot: followers={snapshot.get('follower_count')}, "
                    f"employees={snapshot.get('employee_count')}"
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  ✗ Error: {e}"))

        self.stdout.write(self.style.SUCCESS("\nDone."))
