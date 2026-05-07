"""
Seed dummy data for report generation testing.
Usage: python manage.py seed_report_data
       python manage.py seed_report_data --username admin
       python manage.py seed_report_data --flush   (clears existing dummy data first)
"""
import hashlib
import random
from datetime import date, timedelta, datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from apps.monitoring.models import Competitor, HTMLSnapshot, HTMLDifference
from apps.social_media.models import SocialMediaPost, JobPosting


# ---------------------------------------------------------------------------
# Static dummy content pools
# ---------------------------------------------------------------------------

COMPETITORS = [
    {
        "name": "Honda Pakistan",
        "website_base_url": "https://www.honda.com.pk",
        "linkedin_url": "https://www.linkedin.com/company/honda-atlas-cars-pakistan",
        "twitter_url": "https://twitter.com/HondaPakistan",
    },
    {
        "name": "Suzuki Pakistan",
        "website_base_url": "https://www.suzukipakistan.com",
        "linkedin_url": "https://www.linkedin.com/company/pak-suzuki-motor",
        "twitter_url": "https://twitter.com/SuzukiPakistan",
    },
    {
        "name": "Kia Pakistan",
        "website_base_url": "https://www.kia.com/pk",
        "linkedin_url": "https://www.linkedin.com/company/kia-luck-motors",
        "twitter_url": "https://twitter.com/KiaPakistan",
    },
]

WEBSITE_CHANGES = {
    "Honda Pakistan": [
        {
            "url": "https://www.honda.com.pk/pricing",
            "change_type": "modified",
            "llm_summary": "Honda reduced the price of the City 1.5L variant by PKR 50,000 and introduced a new limited-time financing offer with 0% markup for 12 months.",
            "diff_summary": {
                "added_sections": ["0% markup financing banner", "limited time offer badge"],
                "removed_sections": ["old pricing table footer note"],
                "modified_sections": ["City 1.5L price updated from PKR 4,299,000 to PKR 4,249,000"],
                "total_changes": 4,
            },
        },
        {
            "url": "https://www.honda.com.pk/civic",
            "change_type": "modified",
            "llm_summary": "Honda updated the Civic product page to highlight the new turbo engine variant and added a 360-degree interior view feature.",
            "diff_summary": {
                "added_sections": ["360-degree interior view widget", "turbo badge on hero image"],
                "removed_sections": [],
                "modified_sections": ["hero tagline updated", "engine specs section expanded"],
                "total_changes": 4,
            },
        },
        {
            "url": "https://www.honda.com.pk/new-launch",
            "change_type": "added",
            "llm_summary": "A new page was launched announcing the upcoming Honda HR-V electric variant for the Pakistani market, with a waitlist registration form.",
            "diff_summary": {
                "added_sections": ["entire new page", "HR-V EV announcement", "waitlist form"],
                "removed_sections": [],
                "modified_sections": [],
                "total_changes": 1,
            },
        },
    ],
    "Suzuki Pakistan": [
        {
            "url": "https://www.suzukipakistan.com/alto",
            "change_type": "modified",
            "llm_summary": "Suzuki updated the Alto VXR page with revised color options, adding Pearl White and Graphite Grey while discontinuing Silver Metallic.",
            "diff_summary": {
                "added_sections": ["Pearl White color swatch", "Graphite Grey color swatch"],
                "removed_sections": ["Silver Metallic color option"],
                "modified_sections": ["color selection gallery", "availability note"],
                "total_changes": 5,
            },
        },
        {
            "url": "https://www.suzukipakistan.com/dealers",
            "change_type": "modified",
            "llm_summary": "Suzuki added 3 new dealership locations in Lahore, Multan, and Quetta, expanding their dealer network significantly.",
            "diff_summary": {
                "added_sections": ["Lahore DHA dealer card", "Multan dealer card", "Quetta dealer card"],
                "removed_sections": [],
                "modified_sections": ["dealer count in header updated from 42 to 45"],
                "total_changes": 4,
            },
        },
    ],
    "Kia Pakistan": [
        {
            "url": "https://www.kia.com/pk/sportage",
            "change_type": "modified",
            "llm_summary": "Kia revised the Sportage pricing page with a PKR 75,000 price increase across all variants, citing import cost adjustments.",
            "diff_summary": {
                "added_sections": ["price revision notice banner"],
                "removed_sections": [],
                "modified_sections": [
                    "Sportage Alpha price updated",
                    "Sportage FWD price updated",
                    "Sportage AWD price updated",
                ],
                "total_changes": 4,
            },
        },
        {
            "url": "https://www.kia.com/pk/ev6",
            "change_type": "added",
            "llm_summary": "Kia launched a dedicated EV6 product page for Pakistan, featuring specs, a booking form, and an estimated delivery timeline of Q3 2026.",
            "diff_summary": {
                "added_sections": ["full EV6 product page", "booking CTA", "delivery timeline section"],
                "removed_sections": [],
                "modified_sections": [],
                "total_changes": 1,
            },
        },
    ],
}

SOCIAL_POSTS = {
    "Honda Pakistan": [
        {
            "platform": "linkedin",
            "post_type": "post",
            "content": "Exciting news for our valued customers! Honda Pakistan is proud to introduce flexible financing options with 0% markup for the first 12 months on select models. Drive home your dream Honda today. Visit your nearest dealership for details. #HondaPakistan #AutoFinance",
            "likes": 312, "comments": 47, "shares": 28,
        },
        {
            "platform": "linkedin",
            "post_type": "post",
            "content": "The Honda Civic Turbo is redefining performance on Pakistani roads. With its 1.5L VTEC Turbo engine delivering 178 horsepower, it's built for those who demand more. Book a test drive today. #CivicTurbo #HondaPakistan",
            "likes": 521, "comments": 89, "shares": 64,
        },
        {
            "platform": "linkedin",
            "post_type": "article",
            "content": "At Honda, we believe mobility should be accessible to everyone. That's why we're expanding our certified pre-owned program across 15 new cities in Pakistan this year, bringing quality and reliability to more customers than ever before.",
            "likes": 198, "comments": 33, "shares": 19,
        },
        {
            "platform": "linkedin",
            "post_type": "post",
            "content": "We're thrilled to welcome our newest team members who joined Honda Pakistan this quarter. Our engineering and sales teams are growing to better serve you. #HondaFamily #Careers",
            "likes": 145, "comments": 22, "shares": 8,
        },
    ],
    "Suzuki Pakistan": [
        {
            "platform": "linkedin",
            "post_type": "post",
            "content": "Pak Suzuki celebrates 40 years of manufacturing excellence in Pakistan. From our first Alto rolling off the line to today's diverse lineup, we remain committed to building affordable, reliable vehicles for Pakistani families. #PakSuzuki40Years",
            "likes": 678, "comments": 112, "shares": 95,
        },
        {
            "platform": "linkedin",
            "post_type": "post",
            "content": "The all-new Suzuki Swift Sport is here. Bold design, spirited performance, and the fuel efficiency you expect from Suzuki. Available at dealerships nationwide starting next month. Pre-register now.",
            "likes": 445, "comments": 78, "shares": 52,
        },
        {
            "platform": "linkedin",
            "post_type": "update",
            "content": "Suzuki Pakistan is expanding! We are pleased to announce 3 new dealerships in Lahore, Multan, and Quetta — bringing our total network to 45 locations across the country.",
            "likes": 289, "comments": 44, "shares": 31,
        },
    ],
    "Kia Pakistan": [
        {
            "platform": "linkedin",
            "post_type": "post",
            "content": "The future of driving is electric, and Kia Pakistan is leading the charge. We are proud to announce the official launch of the EV6 in Pakistan — bookings now open. Be among the first to experience true electric performance.",
            "likes": 892, "comments": 167, "shares": 143,
        },
        {
            "platform": "linkedin",
            "post_type": "post",
            "content": "Kia Sportage continues to dominate the SUV segment in Pakistan. With its bold design and advanced safety features, it's no surprise it remains the #1 choice for Pakistani families. Thank you for your trust. #KiaSportage",
            "likes": 534, "comments": 91, "shares": 67,
        },
        {
            "platform": "linkedin",
            "post_type": "article",
            "content": "Global supply chain pressures have impacted vehicle pricing across the industry. Kia Pakistan remains committed to transparency — our recent price revision reflects actual import cost increases, and we continue to offer the best value in our segment.",
            "likes": 201, "comments": 58, "shares": 24,
        },
        {
            "platform": "linkedin",
            "post_type": "post",
            "content": "Kia Pakistan is investing in our people. We are hiring across engineering, digital marketing, and customer experience teams. Join a global brand that's growing fast in Pakistan. #KiaCareers #NowHiring",
            "likes": 178, "comments": 39, "shares": 21,
        },
    ],
}

JOB_POSTINGS = {
    "Honda Pakistan": [
        {
            "job_id": "honda-pk-001",
            "title": "Senior Automotive Engineer",
            "location": "Lahore, Pakistan",
            "employment_type": "Full-time",
            "seniority_level": "Senior",
            "job_function": "Engineering",
            "industries": "Automotive",
            "description": "Lead engineering projects for next-generation Honda vehicles manufactured in Pakistan. Oversee quality control and production optimization.",
        },
        {
            "job_id": "honda-pk-002",
            "title": "Digital Marketing Manager",
            "location": "Karachi, Pakistan",
            "employment_type": "Full-time",
            "seniority_level": "Mid-Senior",
            "job_function": "Marketing",
            "industries": "Automotive",
            "description": "Drive Honda Pakistan's digital presence across social media, SEO, and paid campaigns. Manage a team of 4 digital marketers.",
        },
        {
            "job_id": "honda-pk-003",
            "title": "EV Systems Specialist",
            "location": "Lahore, Pakistan",
            "employment_type": "Full-time",
            "seniority_level": "Mid-Senior",
            "job_function": "Engineering",
            "industries": "Automotive / Electric Vehicles",
            "description": "Develop and validate electric vehicle systems for Honda's upcoming EV lineup in Pakistan. Experience with BMS and charging infrastructure required.",
        },
    ],
    "Suzuki Pakistan": [
        {
            "job_id": "suzuki-pk-001",
            "title": "Production Supervisor",
            "location": "Karachi, Pakistan",
            "employment_type": "Full-time",
            "seniority_level": "Mid-Senior",
            "job_function": "Manufacturing",
            "industries": "Automotive",
            "description": "Supervise daily production operations at the Pak Suzuki manufacturing plant. Ensure quality standards and production targets are met.",
        },
        {
            "job_id": "suzuki-pk-002",
            "title": "Regional Sales Manager",
            "location": "Lahore, Pakistan",
            "employment_type": "Full-time",
            "seniority_level": "Senior",
            "job_function": "Sales",
            "industries": "Automotive",
            "description": "Lead sales operations across the Punjab region. Manage dealer relationships and achieve monthly sales targets.",
        },
    ],
    "Kia Pakistan": [
        {
            "job_id": "kia-pk-001",
            "title": "EV Infrastructure Engineer",
            "location": "Islamabad, Pakistan",
            "employment_type": "Full-time",
            "seniority_level": "Senior",
            "job_function": "Engineering",
            "industries": "Automotive / Electric Vehicles",
            "description": "Design and deploy EV charging infrastructure across Pakistan for Kia's growing EV customer base. Coordinate with government bodies and third-party partners.",
        },
        {
            "job_id": "kia-pk-002",
            "title": "Customer Experience Manager",
            "location": "Karachi, Pakistan",
            "employment_type": "Full-time",
            "seniority_level": "Mid-Senior",
            "job_function": "Customer Service",
            "industries": "Automotive",
            "description": "Own the end-to-end customer journey at Kia Pakistan. Implement NPS programs, resolve escalations, and drive satisfaction scores.",
        },
        {
            "job_id": "kia-pk-003",
            "title": "Senior Software Developer (Connected Cars)",
            "location": "Lahore, Pakistan",
            "employment_type": "Full-time",
            "seniority_level": "Senior",
            "job_function": "Technology",
            "industries": "Automotive / Software",
            "description": "Build and maintain Kia Connect platform features for Pakistani market. Work on telematics, OTA updates, and mobile app integrations.",
        },
        {
            "job_id": "kia-pk-004",
            "title": "Digital Marketing Specialist",
            "location": "Karachi, Pakistan",
            "employment_type": "Full-time",
            "seniority_level": "Associate",
            "job_function": "Marketing",
            "industries": "Automotive",
            "description": "Execute Kia Pakistan's social media and performance marketing campaigns. Strong knowledge of Meta Ads and Google Ads required.",
        },
    ],
}


class Command(BaseCommand):
    help = 'Seed dummy competitor data for report generation testing'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default=None, help='Username to attach data to')
        parser.add_argument('--flush', action='store_true', help='Delete existing dummy data before seeding')

    def handle(self, *args, **options):
        user = self._get_user(options['username'])
        if not user:
            return

        if options['flush']:
            self._flush(user)

        self.stdout.write(f'\nSeeding data for user: {user.username}')

        for comp_data in COMPETITORS:
            competitor = self._create_competitor(user, comp_data)
            self._create_website_changes(competitor)
            self._create_social_posts(competitor)
            self._create_job_postings(competitor)

        self.stdout.write(self.style.SUCCESS('\nDone! Database seeded successfully.'))
        self.stdout.write('You can now test report generation via POST /api/reports/generate/')

    # ------------------------------------------------------------------

    def _get_user(self, username):
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{username}" not found.'))
                return None

        users = User.objects.all()
        if not users.exists():
            self.stdout.write(self.style.ERROR('No users found. Create a user first.'))
            return None

        user = users.first()
        self.stdout.write(f'No --username given, using first user: {user.username}')
        return user

    def _flush(self, user):
        self.stdout.write('Flushing existing dummy data...')
        names = [c['name'] for c in COMPETITORS]
        competitors = Competitor.objects.filter(user=user, name__in=names)
        for c in competitors:
            HTMLDifference.objects.filter(competitor=c).delete()
            HTMLSnapshot.objects.filter(competitor=c).delete()
            SocialMediaPost.objects.filter(competitor=c).delete()
            JobPosting.objects.filter(competitor=c).delete()
        competitors.delete()
        self.stdout.write('  Flushed.')

    def _create_competitor(self, user, data):
        competitor, created = Competitor.objects.get_or_create(
            user=user,
            website_base_url=data['website_base_url'],
            defaults={
                'name': data['name'],
                'linkedin_url': data.get('linkedin_url', ''),
                'twitter_url': data.get('twitter_url', ''),
                'is_deleted': False,
            }
        )
        label = 'Created' if created else 'Already exists'
        self.stdout.write(f'  [{label}] Competitor: {competitor.name}')
        return competitor

    def _random_days_ago(self, min_days=0, max_days=6):
        days = random.randint(min_days, max_days)
        return timezone.now() - timedelta(days=days, hours=random.randint(0, 23))

    def _create_website_changes(self, competitor):
        changes = WEBSITE_CHANGES.get(competitor.name, [])
        count = 0
        for change in changes:
            detected_at = self._random_days_ago(0, 6)

            old_html = f'<html><body><h1>{competitor.name} old page</h1></body></html>'
            new_html = f'<html><body><h1>{competitor.name} updated page</h1><p>{change["llm_summary"]}</p></body></html>'

            old_hash = hashlib.sha256(old_html.encode()).hexdigest()
            new_hash = hashlib.sha256(new_html.encode()).hexdigest()

            old_snap = HTMLSnapshot.objects.create(
                competitor=competitor,
                url=change['url'],
                html_content=old_html,
                content_hash=old_hash,
            )
            old_snap.snapshot_at = detected_at - timedelta(days=1)
            old_snap.save()

            new_snap = HTMLSnapshot.objects.create(
                competitor=competitor,
                url=change['url'],
                html_content=new_html,
                content_hash=new_hash,
            )

            diff, created = HTMLDifference.objects.get_or_create(
                competitor=competitor,
                url=change['url'],
                new_snapshot=new_snap,
                defaults={
                    'old_snapshot': old_snap if change['change_type'] != 'added' else None,
                    'change_type': change['change_type'],
                    'diff_summary': change['diff_summary'],
                    'detailed_diff': [],
                    'is_significant': True,
                    'llm_summary': change['llm_summary'],
                }
            )
            if created:
                diff.detected_at = detected_at
                diff.save()
                count += 1

        self.stdout.write(f'    Website changes: {count} inserted')

    def _create_social_posts(self, competitor):
        posts_data = SOCIAL_POSTS.get(competitor.name, [])
        count = 0
        for i, post in enumerate(posts_data):
            post_id = f"{competitor.name.lower().replace(' ', '-')}-post-{i+1}"
            posted_at = self._random_days_ago(0, 6)

            _, created = SocialMediaPost.objects.get_or_create(
                competitor=competitor,
                platform=post['platform'],
                post_id=post_id,
                defaults={
                    'content': post['content'],
                    'post_type': post['post_type'],
                    'post_url': f"{competitor.linkedin_url or ''}/posts/{post_id}",
                    'posted_at': posted_at,
                    'author_name': competitor.name,
                    'author_headline': 'Official Company Page',
                    'num_likes': post['likes'],
                    'num_comments': post['comments'],
                    'num_shares': post['shares'],
                }
            )
            if created:
                count += 1

        self.stdout.write(f'    Social posts: {count} inserted')

    def _create_job_postings(self, competitor):
        jobs_data = JOB_POSTINGS.get(competitor.name, [])
        count = 0
        for job in jobs_data:
            first_seen = self._random_days_ago(0, 6)
            posted_at = first_seen - timedelta(hours=random.randint(1, 12))

            _, created = JobPosting.objects.get_or_create(
                competitor=competitor,
                job_id=job['job_id'],
                defaults={
                    'title': job['title'],
                    'location': job['location'],
                    'employment_type': job['employment_type'],
                    'seniority_level': job['seniority_level'],
                    'job_function': job['job_function'],
                    'industries': job['industries'],
                    'description': job['description'],
                    'job_url': f"https://www.linkedin.com/jobs/{job['job_id']}",
                    'posted_at': posted_at,
                    'is_new': True,
                    'is_active': True,
                }
            )
            if created:
                count += 1

        self.stdout.write(f'    Job postings: {count} inserted')
