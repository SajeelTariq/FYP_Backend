"""
Management command to add dummy HTML tracking data for testing.
Usage: python manage.py add_dummy_html_tracking
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import hashlib
from apps.monitoring.models import Competitor, HTMLSnapshot, HTMLDifference


class Command(BaseCommand):
    help = 'Add dummy HTML tracking data for testing HTML difference detection'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Adding dummy HTML tracking data...'))

        # Get or create a test competitor
        competitors = Competitor.objects.filter(is_deleted=False)
        if not competitors.exists():
            self.stdout.write(self.style.ERROR('No competitors found! Please create at least one competitor first.'))
            return

        competitor = competitors.first()
        self.stdout.write(f'Using competitor: {competitor.name}')

        # Sample URLs
        test_urls = [
            f"{competitor.website_base_url or 'https://example.com'}/products",
            f"{competitor.website_base_url or 'https://example.com'}/pricing",
            f"{competitor.website_base_url or 'https://example.com'}/about",
        ]

        # Clear existing dummy data for this competitor (optional)
        self.stdout.write('Clearing existing snapshots and differences...')
        HTMLDifference.objects.filter(competitor=competitor, url__in=test_urls).delete()
        HTMLSnapshot.objects.filter(competitor=competitor, url__in=test_urls).delete()

        snapshots_created = 0
        differences_created = 0

        for idx, url in enumerate(test_urls, 1):
            # Create old snapshot (7 days ago)
            old_html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Product {idx} - Old Version</title></head>
            <body>
                <h1>Welcome to Product {idx}</h1>
                <div class="price">
                    <p>Price: $99.99</p>
                    <p>Available in stock</p>
                </div>
                <div class="features">
                    <h2>Features</h2>
                    <ul>
                        <li>Feature A</li>
                        <li>Feature B</li>
                    </ul>
                </div>
                <div class="description">
                    <p>This is the old description of our amazing product.</p>
                </div>
            </body>
            </html>
            """
            
            old_hash = hashlib.sha256(old_html.encode()).hexdigest()
            old_snapshot = HTMLSnapshot.objects.create(
                competitor=competitor,
                url=url,
                html_content=old_html,
                content_hash=old_hash,
            )
            # Manually set the created time to 7 days ago
            old_snapshot.snapshot_at = timezone.now() - timedelta(days=7)
            old_snapshot.save()
            snapshots_created += 1

            # Create new snapshot (today) with changes
            new_html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Product {idx} - New Version</title></head>
            <body>
                <h1>Welcome to Product {idx} - NOW WITH UPDATES!</h1>
                <div class="price">
                    <p>Price: $89.99</p>
                    <p class="stock-status">Limited stock available</p>
                    <p class="discount">Special offer: 10% off!</p>
                </div>
                <div class="features">
                    <h2>Features</h2>
                    <ul>
                        <li>Feature A - Enhanced</li>
                        <li>Feature B</li>
                        <li>Feature C - NEW!</li>
                        <li>Feature D - Premium</li>
                    </ul>
                </div>
                <div class="description">
                    <p>This is the NEW and improved description of our amazing product with more details.</p>
                    <p>We've added new capabilities and enhanced performance.</p>
                </div>
                <div class="testimonials">
                    <h2>Customer Reviews</h2>
                    <p>"Absolutely love it!" - Customer A</p>
                </div>
            </body>
            </html>
            """
            
            new_hash = hashlib.sha256(new_html.encode()).hexdigest()
            new_snapshot = HTMLSnapshot.objects.create(
                competitor=competitor,
                url=url,
                html_content=new_html,
                content_hash=new_hash,
            )
            snapshots_created += 1

            # Create HTML difference entry
            diff_summary = {
                "added_sections": [
                    "discount pricing section",
                    "new features (Feature C, Feature D)",
                    "customer testimonials section"
                ],
                "removed_sections": [],
                "modified_sections": [
                    "title updated with 'NOW WITH UPDATES!'",
                    "price reduced from $99.99 to $89.99",
                    "stock status changed to 'Limited stock'",
                    "description expanded with new details"
                ],
                "total_changes": 7
            }

            detailed_diff = [
                {
                    "type": "modified",
                    "section": "title",
                    "old_value": f"Product {idx} - Old Version",
                    "new_value": f"Product {idx} - New Version",
                    "line_number": 4
                },
                {
                    "type": "modified",
                    "section": "h1",
                    "old_value": f"Welcome to Product {idx}",
                    "new_value": f"Welcome to Product {idx} - NOW WITH UPDATES!",
                    "line_number": 6
                },
                {
                    "type": "modified",
                    "section": "price",
                    "old_value": "Price: $99.99",
                    "new_value": "Price: $89.99",
                    "line_number": 8
                },
                {
                    "type": "modified",
                    "section": "stock_status",
                    "old_value": "Available in stock",
                    "new_value": "Limited stock available",
                    "line_number": 9
                },
                {
                    "type": "added",
                    "section": "discount",
                    "new_value": "Special offer: 10% off!",
                    "line_number": 10
                },
                {
                    "type": "added",
                    "section": "features",
                    "new_value": "Feature C - NEW!",
                    "line_number": 16
                },
                {
                    "type": "added",
                    "section": "features",
                    "new_value": "Feature D - Premium",
                    "line_number": 17
                },
                {
                    "type": "modified",
                    "section": "description",
                    "old_value": "This is the old description of our amazing product.",
                    "new_value": "This is the NEW and improved description of our amazing product with more details. We've added new capabilities and enhanced performance.",
                    "line_number": 21
                },
                {
                    "type": "added",
                    "section": "testimonials",
                    "new_value": "Customer Reviews section with testimonial",
                    "line_number": 25
                }
            ]

            # Create difference record for modified content
            HTMLDifference.objects.create(
                competitor=competitor,
                url=url,
                old_snapshot=old_snapshot,
                new_snapshot=new_snapshot,
                change_type='modified',
                diff_summary=diff_summary,
                detailed_diff=detailed_diff,
                is_significant=True  # Mark as significant for RAG update
            )
            differences_created += 1

            self.stdout.write(f'  ✓ Created snapshots and difference for {url}')

        # Create one example with only additions (new page)
        new_page_url = f"{competitor.website_base_url or 'https://example.com'}/new-product-launch"
        new_page_html = """
        <!DOCTYPE html>
        <html>
        <head><title>New Product Launch</title></head>
        <body>
            <h1>Exciting New Product Launch!</h1>
            <div class="announcement">
                <p>We're thrilled to announce our latest innovation.</p>
                <p>Coming soon: Revolutionary Product X</p>
            </div>
            <div class="features">
                <h2>What's New</h2>
                <ul>
                    <li>Cutting-edge technology</li>
                    <li>Eco-friendly design</li>
                    <li>Affordable pricing</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        new_page_hash = hashlib.sha256(new_page_html.encode()).hexdigest()
        new_page_snapshot = HTMLSnapshot.objects.create(
            competitor=competitor,
            url=new_page_url,
            html_content=new_page_html,
            content_hash=new_page_hash,
        )
        snapshots_created += 1

        HTMLDifference.objects.create(
            competitor=competitor,
            url=new_page_url,
            old_snapshot=None,  # No old snapshot - completely new page
            new_snapshot=new_page_snapshot,
            change_type='added',
            diff_summary={
                "added_sections": [
                    "entire new page",
                    "product launch announcement",
                    "features list"
                ],
                "removed_sections": [],
                "modified_sections": [],
                "total_changes": 1
            },
            detailed_diff=[
                {
                    "type": "added",
                    "section": "page",
                    "new_value": "Complete new page: New Product Launch",
                    "line_number": 0
                }
            ],
            is_significant=True
        )
        differences_created += 1

        self.stdout.write(f'  ✓ Created new page snapshot and difference for {new_page_url}')

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully created {snapshots_created} HTML snapshots and {differences_created} differences!'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Competitor: {competitor.name} (ID: {competitor.id})'
        ))
        self.stdout.write(self.style.WARNING(
            '\nYou can now query these differences using the API or admin panel.'
        ))
