from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import authenticate, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q

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
    
    def create(self, request, *args, **kwargs):
        """Create or update competitor with duplicate checking."""
        serializer = CompetitorCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = request.user
        
        # Check if competitor exists by website_base_url or other URLs
        existing_competitor = None
        
        # Try to find by website URL
        if data.get('website_base_url'):
            existing_competitor = Competitor.objects.filter(
                user=user,
                website_base_url=data['website_base_url'],
                is_deleted=False
            ).first()
        
        # If not found by website, try to find by other social media URLs
        if not existing_competitor:
            query = Q()
            if data.get('linkedin_url'):
                query |= Q(linkedin_url=data['linkedin_url'])
            if data.get('facebook_url'):
                query |= Q(facebook_url=data['facebook_url'])
            if data.get('instagram_url'):
                query |= Q(instagram_url=data['instagram_url'])
            if data.get('twitter_url'):
                query |= Q(twitter_url=data['twitter_url'])
            
            if query:
                existing_competitor = Competitor.objects.filter(
                    query, user=user, is_deleted=False
                ).first()
        
        if existing_competitor:
            # Update existing competitor with new URLs if provided
            updated = False
            for field in ['website_base_url', 'linkedin_url', 'facebook_url', 'instagram_url', 'twitter_url']:
                if data.get(field) and not getattr(existing_competitor, field):
                    setattr(existing_competitor, field, data[field])
                    updated = True
            
            # Update name if different
            if data.get('name') and data['name'] != existing_competitor.name:
                existing_competitor.name = data['name']
                updated = True
            
            if updated:
                existing_competitor.save()
                return Response({
                    'message': 'Competitor updated successfully',
                    'competitor': CompetitorSerializer(existing_competitor).data,
                    'created': False
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': 'Competitor already exists with these details',
                    'competitor': CompetitorSerializer(existing_competitor).data,
                    'created': False
                }, status=status.HTTP_200_OK)
        else:
            # Create new competitor
            competitor = Competitor.objects.create(
                user=user,
                name=data['name'],
                website_base_url=data.get('website_base_url') or None,
                linkedin_url=data.get('linkedin_url') or None,
                facebook_url=data.get('facebook_url') or None,
                instagram_url=data.get('instagram_url') or None,
                twitter_url=data.get('twitter_url') or None
            )
            
            return Response({
                'message': 'Competitor created successfully',
                'competitor': CompetitorSerializer(competitor).data,
                'created': True
            }, status=status.HTTP_201_CREATED)
    
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
        allowed_fields = ['name', 'website_base_url', 'linkedin_url', 'facebook_url', 'instagram_url', 'twitter_url']
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

