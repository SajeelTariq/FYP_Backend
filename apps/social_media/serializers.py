from rest_framework import serializers
from .models import SocialMediaPost, JobPosting, SocialMediaSnapshot


class SocialMediaPostSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)

    class Meta:
        model = SocialMediaPost
        fields = [
            'id', 'competitor', 'competitor_name', 'platform', 'post_id',
            'content', 'post_type', 'post_url', 'posted_at',
            'author_name', 'author_headline',
            'num_likes', 'num_comments', 'num_shares', 'scraped_at',
        ]
        read_only_fields = ['id', 'scraped_at']


class JobPostingSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)

    class Meta:
        model = JobPosting
        fields = [
            'id', 'competitor', 'competitor_name', 'job_id', 'title',
            'location', 'employment_type', 'seniority_level',
            'job_function', 'industries', 'description',
            'job_url', 'apply_url', 'posted_at',
            'is_new', 'is_active', 'first_seen_at', 'last_seen_at',
        ]
        read_only_fields = ['id', 'first_seen_at', 'last_seen_at']


class SocialMediaSnapshotSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)

    class Meta:
        model = SocialMediaSnapshot
        fields = [
            'id', 'competitor', 'competitor_name', 'platform',
            'follower_count', 'employee_count', 'recorded_at',
        ]
        read_only_fields = ['id', 'recorded_at']
