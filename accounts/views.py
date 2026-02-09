# accounts/views.py

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserUpdateSerializer,
    CustomTokenObtainPairSerializer, ChangePasswordSerializer
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from investigations.models import Investigation
from entities.models import Entity, Relationship
from evidence.models import Evidence


User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view with additional user data"""
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """Logout endpoint (blacklist refresh token)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserSerializer
        return UserUpdateSerializer
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            
            # Check old password
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {"old_password": "Wrong password."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response(
                {"message": "Password changed successfully"},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Get dashboard statistics for the current user.
    
    GET /api/v1/auth/dashboard/stats/?time_range=7d
    
    Query Params:
    - time_range: 24h, 7d, 30d, 90d (default: 7d)
    """
    user = request.user
    time_range = request.query_params.get('time_range', '7d')
    
    # Calculate date range
    now = timezone.now()
    if time_range == '24h':
        start_date = now - timedelta(hours=24)
    elif time_range == '30d':
        start_date = now - timedelta(days=30)
    elif time_range == '90d':
        start_date = now - timedelta(days=90)
    else:  # 7d default
        start_date = now - timedelta(days=7)
    
    # Get previous period for comparison
    period_days = (now - start_date).days or 1
    previous_start = start_date - timedelta(days=period_days)
    
    # Active investigations (current period)
    active_investigations_current = Investigation.objects.filter(
        user=user,
        status__in=['running', 'paused'],
        created_at__gte=start_date
    ).count()
    
    # Active investigations (previous period)
    active_investigations_previous = Investigation.objects.filter(
        user=user,
        status__in=['running', 'paused'],
        created_at__gte=previous_start,
        created_at__lt=start_date
    ).count()
    
    # Calculate change
    active_change = active_investigations_current - active_investigations_previous
    
    # Total entities
    total_entities_current = Entity.objects.filter(
        investigation__user=user,
        created_at__gte=start_date
    ).count()
    
    total_entities_previous = Entity.objects.filter(
        investigation__user=user,
        created_at__gte=previous_start,
        created_at__lt=start_date
    ).count()
    
    entities_change = total_entities_current - total_entities_previous
    
    # Total documents (evidence)
    total_documents_current = Evidence.objects.filter(
        investigation__user=user,
        created_at__gte=start_date
    ).count()
    
    total_documents_previous = Evidence.objects.filter(
        investigation__user=user,
        created_at__gte=previous_start,
        created_at__lt=start_date
    ).count()
    
    documents_change = total_documents_current - total_documents_previous
    documents_change_pct = (
        int((documents_change / total_documents_previous) * 100) 
        if total_documents_previous > 0 else 0
    )
    
    # All-time totals
    total_investigations = Investigation.objects.filter(user=user).count()
    total_entities_all = Entity.objects.filter(investigation__user=user).count()
    total_documents_all = Evidence.objects.filter(investigation__user=user).count()
    
    # Team members (placeholder - you might have a team model)
    team_members = 1  # Just the user for now
    
    return Response({
        'active_investigations': {
            'value': active_investigations_current,
            'total': Investigation.objects.filter(
                user=user, 
                status__in=['running', 'paused']
            ).count(),
            'change': f"+{active_change}" if active_change >= 0 else str(active_change),
            'trend': 'up' if active_change >= 0 else 'down'
        },
        'entities_mapped': {
            'value': total_entities_all,
            'change': f"+{entities_change}" if entities_change >= 0 else str(entities_change),
            'trend': 'up' if entities_change >= 0 else 'down'
        },
        'documents_analyzed': {
            'value': total_documents_all,
            'change': f"+{documents_change_pct}%" if documents_change_pct >= 0 else f"{documents_change_pct}%",
            'trend': 'up' if documents_change >= 0 else 'down'
        },
        'team_members': {
            'value': team_members,
            'change': '+0',
            'trend': 'up'
        },
        'time_range': time_range,
        'period_start': start_date.isoformat(),
        'period_end': now.isoformat()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_activity(request):
    """
    Get recent activity feed for dashboard.
    
    GET /api/v1/auth/dashboard/activity/?limit=10
    """
    user = request.user
    limit = int(request.query_params.get('limit', 10))
    
    activities = []
    
    # Recent investigations created
    recent_investigations = Investigation.objects.filter(
        user=user
    ).order_by('-created_at')[:5]
    
    for inv in recent_investigations:
        activities.append({
            'id': f'inv_{inv.id}',
            'user': 'You',
            'action': 'created new investigation',
            'target': inv.title,
            'time': _time_ago(inv.created_at),
            'timestamp': inv.created_at.isoformat(),
            'type': 'investigation_created',
            'icon': 'Search',
            'color': '#6366f1'
        })
    
    # Recent entities discovered
    recent_entities = Entity.objects.filter(
        investigation__user=user
    ).select_related('investigation').order_by('-created_at')[:5]
    
    for entity in recent_entities:
        activities.append({
            'id': f'ent_{entity.id}',
            'user': 'System',
            'action': f'discovered new {entity.entity_type}',
            'target': entity.investigation.title,
            'time': _time_ago(entity.created_at),
            'timestamp': entity.created_at.isoformat(),
            'type': 'entity_discovered',
            'icon': 'Network',
            'color': '#8b5cf6'
        })
    
    # Recent evidence uploaded
    recent_evidence = Evidence.objects.filter(
        investigation__user=user
    ).select_related('investigation').order_by('-created_at')[:5]
    
    for evidence in recent_evidence:
        activities.append({
            'id': f'ev_{evidence.id}',
            'user': 'You',
            'action': 'uploaded document to',
            'target': evidence.investigation.title,
            'time': _time_ago(evidence.created_at),
            'timestamp': evidence.created_at.isoformat(),
            'type': 'evidence_uploaded',
            'icon': 'FileText',
            'color': '#10b981'
        })
    
    # Completed investigations
    completed_investigations = Investigation.objects.filter(
        user=user,
        status='completed'
    ).order_by('-completed_at')[:3]
    
    for inv in completed_investigations:
        if inv.completed_at:
            activities.append({
                'id': f'comp_{inv.id}',
                'user': 'System',
                'action': 'completed analysis of',
                'target': inv.title,
                'time': _time_ago(inv.completed_at),
                'timestamp': inv.completed_at.isoformat(),
                'type': 'investigation_completed',
                'icon': 'Zap',
                'color': '#f59e0b'
            })
    
    # Sort by timestamp (most recent first)
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Limit results
    activities = activities[:limit]
    
    return Response({
        'activities': activities,
        'total': len(activities)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_status(request):
    """
    Get system status for dashboard.
    
    GET /api/v1/auth/dashboard/system-status/
    """
    # These would be real metrics in production
    # For now, return dummy data
    
    from investigations.models import Investigation
    
    # Count queued jobs (pending investigations)
    queued_jobs = Investigation.objects.filter(
        user=request.user,
        status='pending'
    ).count()
    
    return Response({
        'status': 'operational',
        'api_response_time': '24ms',
        'processing_queue': queued_jobs,
        'uptime': '99.9%',
        'last_updated': timezone.now().isoformat()
    })


def _time_ago(dt):
    """Convert datetime to human-readable 'time ago' format"""
    if not dt:
        return 'Unknown'
    
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"