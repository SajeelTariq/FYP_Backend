from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.utils import timezone

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from .models import Role, RolePermission, UserProfile, AlertPreference
from .serializers import (
    RoleSerializer,
    RolePermissionSerializer,
    UserListSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    AlertPreferenceSerializer,
)
from .permissions import HasSettingsPermission


# ---------------------------------------------------------------------------
# Role Views
# Accessible by: super_admin + users with settings=True role permission
# Scoped to:     roles created by the current user
# ---------------------------------------------------------------------------

class RoleListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasSettingsPermission]

    def get(self, request):
        if request.user.profile.user_type == 'super_admin':
            roles = Role.objects.all().select_related('permissions')
        else:
            roles = Role.objects.filter(
                created_by=request.user
            ).select_related('permissions')
        return Response(RoleSerializer(roles, many=True).data)

    def post(self, request):
        serializer = RoleSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            role = serializer.save()
            return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoleDetailView(APIView):
    permission_classes = [IsAuthenticated, HasSettingsPermission]

    def _get_role(self, pk):
        if self.request.user.profile.user_type == 'super_admin':
            return get_object_or_404(Role, pk=pk)
        return get_object_or_404(Role, pk=pk, created_by=self.request.user)

    def get(self, request, pk):
        return Response(RoleSerializer(self._get_role(pk)).data)

    def put(self, request, pk):
        role = self._get_role(pk)
        serializer = RoleSerializer(role, data=request.data, context={'request': request})
        if serializer.is_valid():
            role = serializer.save()
            return Response(RoleSerializer(role).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        self._get_role(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RolePermissionView(APIView):
    """PATCH page-level permissions for a role."""
    permission_classes = [IsAuthenticated, HasSettingsPermission]

    def patch(self, request, pk):
        if request.user.profile.user_type == 'super_admin':
            role = get_object_or_404(Role, pk=pk)
        else:
            role = get_object_or_404(Role, pk=pk, created_by=request.user)
        permissions, _ = RolePermission.objects.get_or_create(role=role)
        serializer = RolePermissionSerializer(permissions, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# My Permissions View
# Accessible by: any authenticated user
# Returns:       the logged-in user's own page-level permissions from DB
# ---------------------------------------------------------------------------

class MyPermissionsView(APIView):
    """
    GET /api/accounts/me/permissions/
    Returns the current user's permissions derived from their assigned role.
    No special permission required — every logged-in user can call this.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'User profile not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if profile.user_type == 'super_admin':
            return Response({
                'dashboard': True,
                'competitors': True,
                'ai_assistant': True,
                'reports': True,
                'settings': True,
                'alerts': True,
                'user_type': 'super_admin',
            })

        if profile.role is None:
            return Response({
                'dashboard': False,
                'competitors': False,
                'ai_assistant': False,
                'reports': False,
                'settings': False,
                'alerts': False,
                'user_type': profile.user_type,
            })

        try:
            perms = profile.role.permissions
            return Response({
                'dashboard': perms.dashboard,
                'competitors': perms.competitors,
                'ai_assistant': perms.ai_assistant,
                'reports': perms.reports,
                'settings': perms.settings,
                'alerts': perms.alerts,
                'user_type': profile.user_type,
            })
        except RolePermission.DoesNotExist:
            return Response({
                'dashboard': False,
                'competitors': False,
                'ai_assistant': False,
                'reports': False,
                'settings': False,
                'alerts': False,
                'user_type': profile.user_type,
            })


# ---------------------------------------------------------------------------
# User Views
# Accessible by: super_admin + users with settings=True role permission
# Scoped to:     users created by the current user (created_by=request.user)
#                — an admin cannot see other admins' users
# ---------------------------------------------------------------------------

class UserListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasSettingsPermission]

    def get(self, request):
        utype = request.user.profile.user_type
        if utype == 'super_admin':
            profiles = UserProfile.objects.filter(
                is_deleted=False
            ).select_related('user', 'role')
        else:
            profiles = UserProfile.objects.filter(
                created_by=request.user, is_deleted=False
            ).select_related('user', 'role')
        users = [p.user for p in profiles]
        return Response(UserListSerializer(users, many=True).data)

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserListSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, HasSettingsPermission]

    def _get_profile(self, pk):
        if self.request.user.profile.user_type == 'super_admin':
            return get_object_or_404(UserProfile, user__pk=pk, is_deleted=False)
        return get_object_or_404(
            UserProfile, user__pk=pk, created_by=self.request.user, is_deleted=False
        )

    def get(self, request, pk):
        return Response(UserListSerializer(self._get_profile(pk).user).data)

    def put(self, request, pk):
        user = self._get_profile(pk).user
        serializer = UserUpdateSerializer(
            data=request.data,
            context={'request': request, 'user_instance': user},
        )
        if serializer.is_valid():
            user = serializer.update(user, serializer.validated_data)
            return Response(UserListSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Soft delete — sets is_deleted=True, does NOT remove from DB."""
        self._get_profile(pk).soft_delete()
        return Response({'detail': 'User deleted successfully.'}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Alert Preference View
# GET  /api/accounts/me/alert-preference/  → get own preferences
# PATCH /api/accounts/me/alert-preference/ → update own preferences
# ---------------------------------------------------------------------------

class AlertPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_or_create_pref(self, user):
        pref, _ = AlertPreference.objects.get_or_create(user=user)
        return pref

    def get(self, request):
        pref = self._get_or_create_pref(request.user)
        return Response(AlertPreferenceSerializer(pref).data)

    def patch(self, request):
        pref = self._get_or_create_pref(request.user)
        serializer = AlertPreferenceSerializer(pref, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AlertsListView(APIView):
    """
    GET /api/accounts/me/alerts/
    Returns recent alerts for the logged-in user aggregated from:
    - HTMLDifference (website changes & new pages)
    - JobPosting (new jobs)
    - SocialMediaSnapshot (follower/employee spikes)

    Query params:
      ?days=7        (default 7, max 30)
      ?type=all|website_changes|new_pages|new_jobs|follower_change
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.monitoring.models import HTMLDifference
        from apps.social_media.models import JobPosting, SocialMediaSnapshot

        days = min(int(request.query_params.get('days', 7)), 30)
        alert_type = request.query_params.get('type', 'all')
        since = timezone.now() - timedelta(days=days)
        user = request.user
        alerts = []

        pref, _ = AlertPreference.objects.get_or_create(user=user)

        if alert_type in ('all', 'website_changes') and pref.notify_website_changes:
            changes = (
                HTMLDifference.objects
                .filter(
                    competitor__user=user,
                    is_significant=True,
                    change_type='modified',
                    detected_at__gte=since,
                    is_onboarding_snapshot=False,
                )
                .select_related('competitor')
                .order_by('-detected_at')
            )
            for c in changes:
                alerts.append({
                    'type': 'website_change',
                    'title': f'{c.competitor.name} — Website Change',
                    'description': c.llm_summary,
                    'meta': {
                        'url': c.url,
                        'change_type': c.change_type,
                        'added_lines': c.diff_summary.get('added_lines', 0),
                        'removed_lines': c.diff_summary.get('removed_lines', 0),
                    },
                    'competitor': c.competitor.name,
                    'timestamp': c.detected_at,
                })

        if alert_type in ('all', 'new_pages') and pref.notify_new_pages:
            new_pages = (
                HTMLDifference.objects
                .filter(
                    competitor__user=user,
                    change_type='added',
                    detected_at__gte=since,
                    is_onboarding_snapshot=False,
                )
                .exclude(diff_summary__has_key='note')
                .select_related('competitor')
                .order_by('-detected_at')
            )
            for p in new_pages:
                alerts.append({
                    'type': 'new_page',
                    'title': f'{p.competitor.name} — New Page Detected',
                    'description': f'New page discovered: {p.url}',
                    'meta': {'url': p.url},
                    'competitor': p.competitor.name,
                    'timestamp': p.detected_at,
                })

        if alert_type in ('all', 'new_jobs') and pref.notify_new_jobs:
            jobs = (
                JobPosting.objects
                .filter(
                    competitor__user=user,
                    is_new=True,
                    first_seen_at__gte=since,
                )
                .select_related('competitor')
                .order_by('-first_seen_at')
            )
            for j in jobs:
                alerts.append({
                    'type': 'new_job',
                    'title': f'{j.competitor.name} — New Job Posted',
                    'description': f'{j.title} · {j.location} · {j.seniority_level}',
                    'meta': {
                        'job_title': j.title,
                        'location': j.location,
                        'seniority': j.seniority_level,
                        'employment_type': j.employment_type,
                        'job_url': j.job_url,
                    },
                    'competitor': j.competitor.name,
                    'timestamp': j.first_seen_at,
                })

        if alert_type in ('all', 'follower_change') and pref.notify_follower_change:
            today = timezone.now().date()
            yesterday = today - timedelta(days=1)
            platform_url_map = {
                'linkedin': 'linkedin_url',
                'facebook': 'facebook_url',
                'instagram': 'instagram_url',
            }
            for comp in user.competitors.filter(is_deleted=False):
                for platform, url_field in platform_url_map.items():
                    if not getattr(comp, url_field, None):
                        continue
                    today_snap = (
                        SocialMediaSnapshot.objects
                        .filter(competitor=comp, platform=platform, recorded_at__date=today)
                        .order_by('-recorded_at').first()
                    )
                    yesterday_snap = (
                        SocialMediaSnapshot.objects
                        .filter(competitor=comp, platform=platform, recorded_at__date=yesterday)
                        .order_by('-recorded_at').first()
                    )
                    if not today_snap or not yesterday_snap:
                        continue

                    f_pct = _pct(yesterday_snap.follower_count, today_snap.follower_count)
                    e_pct = _pct(yesterday_snap.employee_count, today_snap.employee_count)

                    if abs(f_pct) >= 5 or abs(e_pct) >= 5:
                        alerts.append({
                            'type': 'follower_change',
                            'title': f'{comp.name} — {platform.capitalize()} Follower Spike',
                            'description': f'Followers {f_pct:+}% · Employees {e_pct:+}%',
                            'meta': {
                                'platform': platform,
                                'follower_count_old': yesterday_snap.follower_count,
                                'follower_count_new': today_snap.follower_count,
                                'follower_pct': f_pct,
                                'employee_count_old': yesterday_snap.employee_count,
                                'employee_count_new': today_snap.employee_count,
                                'employee_pct': e_pct,
                            },
                            'competitor': comp.name,
                            'timestamp': today_snap.recorded_at,
                        })

        if alert_type in ('all', 'news_mentions') and pref.notify_news_mentions:
            from apps.monitoring.models import NewsArticle
            articles = (
                NewsArticle.objects
                .filter(
                    competitor__user=user,
                    published_at__gte=since,
                )
                .select_related('competitor')
                .order_by('-published_at')
            )
            for a in articles:
                alerts.append({
                    'type': 'news_mention',
                    'title': f'{a.competitor.name} — News Mention',
                    'description': a.title,
                    'meta': {
                        'url': a.url,
                        'source': a.source,
                        'published_at': a.published_at.isoformat() if a.published_at else None,
                    },
                    'competitor': a.competitor.name,
                    'timestamp': a.published_at or a.fetched_at,
                })

        alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        return Response({
            'count': len(alerts),
            'days': days,
            'alerts': alerts,
        })


def _pct(old, new):
    if old is None or new is None or old == 0:
        return 0.0
    return round(((new - old) / old) * 100, 1)


class TestAlertEmailView(APIView):
    """
    POST /api/accounts/me/alert-preference/test-email/
    Sends a test email using current user's alert preference.
    For testing only.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.accounts.email_service import (
            send_website_change_alerts,
            send_job_alerts,
            send_follower_change_alerts,
            send_new_pages_alerts,
        )

        alert_type = request.data.get('type', 'all')

        try:
            if alert_type == 'website_changes':
                send_website_change_alerts()
            elif alert_type == 'new_jobs':
                send_job_alerts()
            elif alert_type == 'follower_change':
                send_follower_change_alerts()
            elif alert_type == 'new_pages':
                send_new_pages_alerts()
            else:
                send_website_change_alerts()
                send_job_alerts()
                send_follower_change_alerts()
                send_new_pages_alerts()

            return Response({'status': 'success', 'message': f'Alert emails triggered: {alert_type}'})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
