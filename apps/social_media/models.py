from django.db import models
from apps.monitoring.models import Competitor


class SocialMediaPost(models.Model):
    PLATFORM_CHOICES = [
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter'),
    ]
    POST_TYPE_CHOICES = [
        ('post', 'Post'),
        ('article', 'Article'),
        ('update', 'Update'),
        ('job', 'Job'),
    ]

    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='social_posts')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    post_id = models.CharField(max_length=255, help_text="Platform-native ID for deduplication")
    content = models.TextField(blank=True)
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default='post')
    post_url = models.URLField(blank=True, null=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    author_name = models.CharField(max_length=255, blank=True)
    author_headline = models.CharField(max_length=500, blank=True)
    num_likes = models.PositiveIntegerField(default=0)
    num_comments = models.PositiveIntegerField(default=0)
    num_shares = models.PositiveIntegerField(default=0)
    scraped_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['competitor', 'platform', 'post_id']]
        ordering = ['-posted_at']
        indexes = [
            models.Index(fields=['competitor', 'platform', '-posted_at']),
            models.Index(fields=['competitor', '-scraped_at']),
        ]

    def __str__(self):
        return f"[{self.platform}] {self.competitor.name} — {self.post_id}"


class JobPosting(models.Model):
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='job_postings')
    job_id = models.CharField(max_length=255, help_text="LinkedIn job ID for deduplication")
    title = models.CharField(max_length=500)
    location = models.CharField(max_length=255, blank=True)
    employment_type = models.CharField(max_length=100, blank=True)
    seniority_level = models.CharField(max_length=100, blank=True)
    job_function = models.CharField(max_length=255, blank=True)
    industries = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    job_url = models.URLField(blank=True, null=True)
    apply_url = models.URLField(blank=True, null=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    # True only on the run it was first seen — useful for alerting
    is_new = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, help_text="False when job no longer appears in scrape")
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['competitor', 'job_id']]
        ordering = ['-first_seen_at']
        indexes = [
            models.Index(fields=['competitor', '-first_seen_at']),
            models.Index(fields=['competitor', 'is_active']),
            models.Index(fields=['is_new']),
        ]

    def __str__(self):
        return f"{self.competitor.name} — {self.title} ({self.location})"


class SocialMediaSnapshot(models.Model):
    """Daily snapshot of follower/employee counts for trend tracking."""
    PLATFORM_CHOICES = [
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter'),
    ]

    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='social_snapshots')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    follower_count = models.PositiveIntegerField(null=True, blank=True)
    employee_count = models.PositiveIntegerField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['competitor', 'platform', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.competitor.name} [{self.platform}] — {self.recorded_at.date()}"
