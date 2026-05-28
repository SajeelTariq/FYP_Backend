from rest_framework import serializers
from .models import (
    Competitor, MonitoringTask, ExtractedLinks, 
    FilteredLinks, DailyScraperLinks, CompetitorHTML, CompetitorMetadata,
    HTMLSnapshot, HTMLDifference
)
from django.contrib.auth.models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']


class CompetitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competitor
        fields = [
            'id', 'name', 'website_base_url', 'linkedin_url',
            'facebook_url', 'instagram_url', 'twitter_url',
            'stock_symbol', 'is_deleted', 'onboarding_status',
            'onboarding_error', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'onboarding_status', 'onboarding_error', 'created_at', 'updated_at']

    def validate(self, data):
        # At least one URL must be provided
        urls = [
            data.get('website_base_url'),
            data.get('linkedin_url'),
            data.get('facebook_url'),
            data.get('instagram_url'),
            data.get('twitter_url')
        ]
        if not any(urls):
            raise serializers.ValidationError(
                "At least one URL (website, LinkedIn, Facebook, Instagram, or Twitter) must be provided"
            )
        return data


class CompetitorCreateUpdateSerializer(serializers.Serializer):
    """Serializer for creating or updating competitors with duplicate checking."""
    name = serializers.CharField(max_length=255)
    website_base_url = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    linkedin_url = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    facebook_url = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    instagram_url = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    twitter_url = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    stock_symbol = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate(self, data):
        # At least one URL must be provided
        urls = [
            data.get('website_base_url'),
            data.get('linkedin_url'),
            data.get('facebook_url'),
            data.get('instagram_url'),
            data.get('twitter_url')
        ]
        if not any(urls):
            raise serializers.ValidationError(
                "At least one URL (website, LinkedIn, Facebook, Instagram, or Twitter) must be provided"
            )
        return data


class MonitoringTaskSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = MonitoringTask
        fields = '__all__'


class ExtractedLinksSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = ExtractedLinks
        fields = '__all__'


class FilteredLinksSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = FilteredLinks
        fields = '__all__'


class DailyScraperLinksSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = DailyScraperLinks
        fields = '__all__'


class CompetitorHTMLSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    html_size = serializers.SerializerMethodField()
    
    class Meta:
        model = CompetitorHTML
        fields = ['id', 'competitor', 'competitor_name', 'url', 'html_size', 'scraped_at']
    
    def get_html_size(self, obj):
        return len(obj.html_content) if obj.html_content else 0


class CompetitorMetadataSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = CompetitorMetadata
        fields = '__all__'


class HTMLSnapshotSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    html_size = serializers.SerializerMethodField()
    
    class Meta:
        model = HTMLSnapshot
        fields = ['id', 'competitor', 'competitor_name', 'url', 'content_hash', 'html_size', 'snapshot_at']
    
    def get_html_size(self, obj):
        return len(obj.html_content) if obj.html_content else 0


class HTMLDifferenceSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    old_snapshot_time = serializers.DateTimeField(source='old_snapshot.snapshot_at', read_only=True, allow_null=True)
    new_snapshot_time = serializers.DateTimeField(source='new_snapshot.snapshot_at', read_only=True)
    
    class Meta:
        model = HTMLDifference
        fields = '__all__'

