"""
Management command to manually trigger the daily monitoring pipeline.

Usage:
    python manage.py run_daily_monitoring
    python manage.py run_daily_monitoring --competitor-id 5
"""
from django.core.management.base import BaseCommand
from apps.scraping.tasks import run_daily_monitoring


class Command(BaseCommand):
    help = "Run the daily competitor monitoring pipeline (all 5 steps)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--competitor-id",
            type=int,
            default=None,
            help="Run pipeline for a single competitor by ID (default: all active competitors)",
        )

    def handle(self, *args, **options):
        competitor_id = options["competitor_id"]

        if competitor_id:
            from apps.monitoring.models import Competitor

            try:
                comp = Competitor.objects.get(pk=competitor_id, is_deleted=False)
            except Competitor.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Competitor {competitor_id} not found or deleted."))
                return

            self.stdout.write(f"Running daily monitoring for: {comp.name}")

            from apps.scraping.tasks import (
                _step1_refresh_links,
                _step2_scrape_html,
                _step3_detect_changes_and_summarize,
                _step4_extract_clean_text,
                _step5_update_embeddings,
            )

            new_links, removed_links, all_links = _step1_refresh_links(comp)
            self.stdout.write(f"  Step 1: {len(all_links)} links (+{len(new_links)} new)")

            scraped = _step2_scrape_html(comp, all_links)
            self.stdout.write(f"  Step 2: Scraped {scraped}/{len(all_links)} pages")

            changes = _step3_detect_changes_and_summarize(comp, all_links)
            self.stdout.write(f"  Step 3: {changes} changes detected")

            processed = _step4_extract_clean_text(comp, all_links)
            self.stdout.write(f"  Step 4: Processed {processed} pages")

            embed_result = _step5_update_embeddings(comp)
            self.stdout.write(f"  Step 5: {embed_result.get('added', 0)} chunks embedded")

            self.stdout.write(self.style.SUCCESS(f"Done: {comp.name}"))
        else:
            self.stdout.write("Running daily monitoring for ALL active competitors...")
            result = run_daily_monitoring()
            self.stdout.write(self.style.SUCCESS(f"Completed: {result}"))
