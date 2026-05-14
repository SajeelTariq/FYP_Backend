from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import authenticate, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
import logging

from .models import (
    Competitor, MonitoringTask, ExtractedLinks, 
    FilteredLinks, DailyScraperLinks, CompetitorHTML, CompetitorMetadata,
    HTMLSnapshot, HTMLDifference
)
from .serializers import (
    CompetitorSerializer, MonitoringTaskSerializer, 
    CompetitorCreateUpdateSerializer, UserRegistrationSerializer,
    UserSerializer, ExtractedLinksSerializer, FilteredLinksSerializer,
    DailyScraperLinksSerializer, CompetitorHTMLSerializer, CompetitorMetadataSerializer,
    HTMLSnapshotSerializer, HTMLDifferenceSerializer
)
from utils.validators import validate_url_exists

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)


class LoginView(ObtainAuthToken):
    """User login endpoint."""
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            })
        
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )


class LogoutView(generics.GenericAPIView):
    """User logout endpoint."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
        except:
            pass
        logout(request)
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)


class CompetitorViewSet(viewsets.ModelViewSet):
    """ViewSet for managing competitors."""
    serializer_class = CompetitorSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return competitors for the current user only."""
        return Competitor.objects.filter(user=self.request.user, is_deleted=False)
    
    def _validate_urls(self, data):
        """
        Validate that all provided URLs actually exist.
        Auto-normalizes URLs (prepends https:// if missing).
        Returns (valid_urls_dict, errors_list).
        """
        url_fields = ['website_base_url', 'linkedin_url', 'facebook_url', 'instagram_url', 'twitter_url']
        errors = []
        validated = {}
        
        for field in url_fields:
            url = data.get(field)
            if url and url.strip():
                url = url.strip()
                is_valid, result = validate_url_exists(url)
                if not is_valid:
                    errors.append(result)
                else:
                    # result is the normalized URL (with https:// prepended if needed)
                    validated[field] = result
            else:
                validated[field] = None
        
        return validated, errors
    
    def _find_existing_competitor(self, user, validated_urls):
        """
        Check if any of the provided URLs already belong to a competitor for this user.
        Returns (competitor_or_none, matching_field_or_none, was_deleted).
        """
        url_fields = ['website_base_url', 'linkedin_url', 'facebook_url', 'instagram_url', 'twitter_url']
        
        for field in url_fields:
            url = validated_urls.get(field)
            if url:
                existing = Competitor.objects.filter(
                    user=user, **{field: url}
                ).first()
                if existing:
                    return existing, field, existing.is_deleted
        
        return None, None, False
    
    def _extract_and_check_links(self, competitor):
        """
        Call Firecrawl to extract subpage links. Returns result dict.
        Enforces MAX_COMPETITOR_LINKS limit.
        """
        from apps.scraping.tasks import extract_competitor_links_sync
        return extract_competitor_links_sync(competitor.id)

    def create(self, request, *args, **kwargs):
        """Create competitor with URL validation and automatic link extraction."""
        serializer = CompetitorCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = request.user
        
        # Step 1: Validate all provided URLs actually exist
        validated_urls, url_errors = self._validate_urls(data)
        if url_errors:
            return Response({
                'error': 'One or more URLs are invalid or unreachable',
                'details': url_errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure at least one valid URL was provided
        if not any(validated_urls.values()):
            return Response({
                'error': 'At least one valid URL must be provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Step 2: Check if any URL already belongs to this user's competitor
        existing_competitor, match_field, was_deleted = self._find_existing_competitor(user, validated_urls)
        
        if existing_competitor:
            if was_deleted:
                # Restore soft-deleted competitor and update with new data
                existing_competitor.is_deleted = False
                existing_competitor.deleted_at = None
                existing_competitor.name = data['name']
                for field, url in validated_urls.items():
                    setattr(existing_competitor, field, url)
                existing_competitor.save()
                
                # Auto-extract links if website_base_url is present
                link_result = None
                if existing_competitor.website_base_url:
                    link_result = self._extract_and_check_links(existing_competitor)
                    if link_result.get('status') == 'error' and 'exceeds the maximum' in link_result.get('message', ''):
                        # Too many links — delete the restored competitor and inform user
                        existing_competitor.is_deleted = True
                        existing_competitor.deleted_at = timezone.now()
                        existing_competitor.save()
                        return Response({
                            'error': link_result['message'],
                            'links_count': link_result.get('links_count', 0)
                        }, status=status.HTTP_400_BAD_REQUEST)
                
                response_data = {
                    'message': 'Competitor restored and updated successfully',
                    'competitor': CompetitorSerializer(existing_competitor).data,
                    'created': False,
                    'restored': True
                }
                if link_result and link_result.get('status') == 'success':
                    response_data['links_extracted'] = link_result['links_count']
                return Response(response_data, status=status.HTTP_200_OK)
            
            # Active competitor already exists with a matching URL
            updated = False
            for field, url in validated_urls.items():
                if url and not getattr(existing_competitor, field):
                    setattr(existing_competitor, field, url)
                    updated = True
            
            if data.get('name') and data['name'] != existing_competitor.name:
                existing_competitor.name = data['name']
                updated = True
            
            if updated:
                existing_competitor.save()
                return Response({
                    'message': f'Competitor already exists (matched on {match_field}). Updated with new details.',
                    'competitor': CompetitorSerializer(existing_competitor).data,
                    'created': False
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': f'Competitor already exists with these details (matched on {match_field})',
                    'competitor': CompetitorSerializer(existing_competitor).data,
                    'created': False
                }, status=status.HTTP_200_OK)
        
        # Step 3: Create new competitor
        competitor = Competitor.objects.create(
            user=user,
            name=data['name'],
            website_base_url=validated_urls.get('website_base_url'),
            linkedin_url=validated_urls.get('linkedin_url'),
            facebook_url=validated_urls.get('facebook_url'),
            instagram_url=validated_urls.get('instagram_url'),
            twitter_url=validated_urls.get('twitter_url'),
            stock_symbol=data.get('stock_symbol') or None,
        )
        
        # Step 4: Auto-extract subpage links if website_base_url is provided
        link_result = None
        if competitor.website_base_url:
            link_result = self._extract_and_check_links(competitor)
            if link_result.get('status') == 'error' and 'exceeds the maximum' in link_result.get('message', ''):
                # Too many links — remove the competitor and inform user
                competitor.delete()
                return Response({
                    'error': link_result['message'],
                    'links_count': link_result.get('links_count', 0)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Trigger one-time 6-day news backfill for new competitor
        if competitor.website_base_url:
            from apps.scraping.tasks import fetch_initial_competitor_news
            fetch_initial_competitor_news.delay(competitor.id)

        response_data = {
            'message': 'Competitor created successfully',
            'competitor': CompetitorSerializer(competitor).data,
            'created': True
        }
        if link_result:
            if link_result.get('status') == 'success':
                response_data['links_extracted'] = link_result['links_count']
            elif link_result.get('status') == 'warning':
                response_data['links_warning'] = link_result.get('message')
            elif link_result.get('status') == 'error':
                response_data['links_error'] = link_result.get('message')
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update competitor information (PUT request - full update)."""
        competitor = self.get_object()
        serializer = CompetitorCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Update all fields
        competitor.name = data['name']
        competitor.website_base_url = data.get('website_base_url') or None
        competitor.linkedin_url = data.get('linkedin_url') or None
        competitor.facebook_url = data.get('facebook_url') or None
        competitor.instagram_url = data.get('instagram_url') or None
        competitor.twitter_url = data.get('twitter_url') or None
        competitor.save()
        
        return Response({
            'message': 'Competitor updated successfully',
            'competitor': CompetitorSerializer(competitor).data
        }, status=status.HTTP_200_OK)
    
    def partial_update(self, request, *args, **kwargs):
        """Partially update competitor information (PATCH request - partial update)."""
        competitor = self.get_object()
        
        # Get the fields that are provided in the request
        allowed_fields = ['name', 'website_base_url', 'linkedin_url', 'facebook_url', 'instagram_url', 'twitter_url', 'stock_symbol']
        update_data = {key: value for key, value in request.data.items() if key in allowed_fields}
        
        if not update_data:
            return Response({
                'error': 'No valid fields provided for update'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update only the provided fields
        for field, value in update_data.items():
            setattr(competitor, field, value if value else None)
        
        competitor.save()
        
        return Response({
            'message': 'Competitor updated successfully',
            'competitor': CompetitorSerializer(competitor).data
        }, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete competitor."""
        competitor = self.get_object()
        competitor.is_deleted = True
        competitor.deleted_at = timezone.now()
        competitor.save()
        
        return Response({
            'message': 'Competitor deleted successfully'
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def extract_links(self, request, pk=None):
        """Extract all subpage links from competitor's website using Firecrawl API."""
        from apps.scraping.tasks import extract_competitor_links
        
        competitor = self.get_object()
        
        # Trigger async task
        task = extract_competitor_links.delay(competitor.id)
        
        return Response({
            'status': 'Task started',
            'message': f'Link extraction started for {competitor.name}',
            'task_id': task.id,
            'competitor': competitor.name
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['post'])
    def scrape_html(self, request, pk=None):
        """Scrape HTML content from competitor's links using Playwright."""
        from apps.scraping.tasks import scrape_competitor_html
        
        competitor = self.get_object()
        use_filtered = request.data.get('use_filtered_links', False)
        
        # Trigger async task
        task = scrape_competitor_html.delay(competitor.id, use_filtered)
        
        return Response({
            'status': 'Task started',
            'message': f'HTML scraping started for {competitor.name}',
            'task_id': task.id,
            'competitor': competitor.name,
            'using_filtered_links': use_filtered
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['post'])
    def extract_metadata(self, request, pk=None):
        """Extract clean text and metadata from scraped HTML for RAG system."""
        from apps.scraping.tasks import extract_competitor_metadata
        
        competitor = self.get_object()
        
        # Trigger async task
        task = extract_competitor_metadata.delay(competitor.id)
        
        return Response({
            'status': 'Task started',
            'message': f'Metadata extraction started for {competitor.name}',
            'task_id': task.id,
            'competitor': competitor.name
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['post'])
    def run_full_pipeline(self, request, pk=None):
        """Run complete scraping pipeline: extract links → scrape HTML → extract metadata."""
        from apps.scraping.tasks import run_full_scraping_pipeline
        
        competitor = self.get_object()
        use_filtered = request.data.get('use_filtered_links', False)
        
        # Trigger async task
        task = run_full_scraping_pipeline.delay(competitor.id, use_filtered)
        
        return Response({
            'status': 'Task started',
            'message': f'Full scraping pipeline started for {competitor.name}',
            'task_id': task.id,
            'competitor': competitor.name,
            'using_filtered_links': use_filtered
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['post'])
    def start_monitoring(self, request, pk=None):
        """Start monitoring a competitor."""
        competitor = self.get_object()
        # Trigger monitoring task (will be implemented with Celery)
        return Response({
            'status': 'Monitoring started',
            'competitor': competitor.name
        })


class MonitoringTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for monitoring tasks."""
    permission_classes = [IsAuthenticated]
    serializer_class = MonitoringTaskSerializer
    filterset_fields = ['competitor', 'status', 'task_type']
    
    def get_queryset(self):
        """Return tasks for current user's competitors only."""
        return MonitoringTask.objects.filter(competitor__user=self.request.user)


class ExtractedLinksViewSet(viewsets.ModelViewSet):
    """ViewSet for extracted links."""
    permission_classes = [IsAuthenticated]
    serializer_class = ExtractedLinksSerializer
    
    def get_queryset(self):
        return ExtractedLinks.objects.filter(competitor__user=self.request.user)


class FilteredLinksViewSet(viewsets.ModelViewSet):
    """ViewSet for filtered links."""
    permission_classes = [IsAuthenticated]
    serializer_class = FilteredLinksSerializer
    
    def get_queryset(self):
        return FilteredLinks.objects.filter(competitor__user=self.request.user)


class DailyScraperLinksViewSet(viewsets.ModelViewSet):
    """ViewSet for daily scraper links."""
    permission_classes = [IsAuthenticated]
    serializer_class = DailyScraperLinksSerializer
    
    def get_queryset(self):
        return DailyScraperLinks.objects.filter(competitor__user=self.request.user)


class CompetitorHTMLViewSet(viewsets.ModelViewSet):
    """ViewSet for competitor HTML content."""
    permission_classes = [IsAuthenticated]
    serializer_class = CompetitorHTMLSerializer
    filterset_fields = ['competitor', 'url']
    
    def get_queryset(self):
        return CompetitorHTML.objects.filter(competitor__user=self.request.user)


class CompetitorMetadataViewSet(viewsets.ModelViewSet):
    """ViewSet for competitor metadata."""
    permission_classes = [IsAuthenticated]
    serializer_class = CompetitorMetadataSerializer
    filterset_fields = ['competitor']
    
    def get_queryset(self):
        return CompetitorMetadata.objects.filter(competitor__user=self.request.user)


class HTMLSnapshotViewSet(viewsets.ModelViewSet):
    """ViewSet for HTML snapshots."""
    permission_classes = [IsAuthenticated]
    serializer_class = HTMLSnapshotSerializer
    filterset_fields = ['competitor', 'url']
    
    def get_queryset(self):
        return HTMLSnapshot.objects.filter(competitor__user=self.request.user)


class HTMLDifferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for HTML differences."""
    permission_classes = [IsAuthenticated]
    serializer_class = HTMLDifferenceSerializer
    filterset_fields = ['competitor', 'url', 'change_type', 'is_significant']
    
    def get_queryset(self):
        return HTMLDifference.objects.filter(competitor__user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def significant_changes(self, request):
        """Get only significant changes that require RAG update."""
        significant = self.get_queryset().filter(is_significant=True)
        serializer = self.get_serializer(significant, many=True)
        return Response({
            'count': significant.count(),
            'changes': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of all HTML differences."""
        queryset = self.get_queryset()
        
        summary = {
            'total_differences': queryset.count(),
            'by_change_type': {
                'added': queryset.filter(change_type='added').count(),
                'removed': queryset.filter(change_type='removed').count(),
                'modified': queryset.filter(change_type='modified').count(),
            },
            'significant_changes': queryset.filter(is_significant=True).count(),
            'by_competitor': {}
        }
        
        # Group by competitor
        for competitor in Competitor.objects.filter(user=request.user, is_deleted=False):
            comp_diffs = queryset.filter(competitor=competitor)
            if comp_diffs.exists():
                summary['by_competitor'][competitor.name] = {
                    'total': comp_diffs.count(),
                    'significant': comp_diffs.filter(is_significant=True).count(),
                    'urls_changed': comp_diffs.values('url').distinct().count()
                }
        
        return Response(summary)

