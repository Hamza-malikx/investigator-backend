# investigations/views.py

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Investigation, InvestigationPlan, SubTask
from .serializers import (
    InvestigationListSerializer, InvestigationDetailSerializer,
    InvestigationCreateSerializer, InvestigationUpdateSerializer,
    InvestigationRedirectSerializer, SubTaskSerializer,
    InvestigationPlanSerializer
)


class InvestigationViewSet(viewsets.ModelViewSet):
    """ViewSet for Investigation CRUD operations"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only access their own investigations"""
        return Investigation.objects.filter(user=self.request.user).select_related('plan')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return InvestigationListSerializer
        elif self.action == 'create':
            return InvestigationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return InvestigationUpdateSerializer
        return InvestigationDetailSerializer
    
    def perform_create(self, serializer):
        """Create investigation and trigger background task"""
        investigation = serializer.save()
        
        # Update status to pending
        investigation.status = 'pending'
        investigation.save()
        
        # Trigger Celery task to start investigation
        from core.tasks import run_investigation
        run_investigation.delay(str(investigation.id)) 
        
        return investigation
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get real-time status of investigation"""
        investigation = self.get_object()
        
        return Response({
            'id': str(investigation.id),
            'status': investigation.status,
            'current_phase': investigation.current_phase,
            'progress_percentage': investigation.progress_percentage,
            'confidence_score': investigation.confidence_score,
            'estimated_completion': investigation.estimated_completion,
            'entities_count': investigation.entities.count(),
            'relationships_count': investigation.relationships.count(),
            'evidence_count': investigation.evidence.count(),
        })
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get detailed progress information"""
        investigation = self.get_object()
        
        # Get subtasks breakdown
        subtasks = investigation.subtasks.all()
        
        return Response({
            'id': str(investigation.id),
            'status': investigation.status,
            'current_phase': investigation.current_phase,
            'progress_percentage': investigation.progress_percentage,
            'total_subtasks': subtasks.count(),
            'completed_subtasks': subtasks.filter(status='completed').count(),
            'in_progress_subtasks': subtasks.filter(status='in_progress').count(),
            'pending_subtasks': subtasks.filter(status='pending').count(),
            'failed_subtasks': subtasks.filter(status='failed').count(),
            'total_api_calls': investigation.total_api_calls,
            'total_cost_usd': str(investigation.total_cost_usd),
        })
    
    @action(detail=True, methods=['post'])
    def redirect(self, request, pk=None):
        """Redirect investigation focus"""
        investigation = self.get_object()
        serializer = InvestigationRedirectSerializer(data=request.data)
        
        if serializer.is_valid():
            if investigation.status not in ['running', 'paused']:
                return Response(
                    {'error': 'Can only redirect running or paused investigations'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update investigation plan
            plan = investigation.plan
            focus = serializer.validated_data['focus']
            priority = serializer.validated_data['priority']
            
            # Add to priority areas
            if not plan.priority_areas:
                plan.priority_areas = []
            plan.priority_areas.insert(0, {
                'focus': focus,
                'priority': priority,
                'timestamp': str(timezone.now())
            })
            plan.save()
            
            # TODO: Signal to Celery task to adjust focus
            # from .tasks import redirect_investigation
            # redirect_investigation.delay(investigation.id, focus, priority)
            
            return Response({
                'message': 'Investigation redirected successfully',
                'new_focus': focus,
                'priority': priority
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause investigation"""
        investigation = self.get_object()
        
        if investigation.status != 'running':
            return Response(
                {'error': 'Can only pause running investigations'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        investigation.status = 'paused'
        investigation.save()
        
        return Response({'message': 'Investigation paused'})
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume paused investigation"""
        investigation = self.get_object()
        
        if investigation.status != 'paused':
            return Response(
                {'error': 'Can only resume paused investigations'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        investigation.status = 'running'
        investigation.save()
        
        # TODO: Trigger Celery task to resume
        # from .tasks import resume_investigation
        # resume_investigation.delay(investigation.id)
        
        return Response({'message': 'Investigation resumed'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel investigation"""
        investigation = self.get_object()
        
        if investigation.status in ['completed', 'failed']:
            return Response(
                {'error': 'Cannot cancel completed or failed investigations'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        investigation.status = 'failed'
        investigation.completed_at = timezone.now()
        investigation.save()
        
        return Response({'message': 'Investigation cancelled'})


class SubTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for SubTask (read-only)"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SubTaskSerializer
    
    def get_queryset(self):
        """Filter by investigation and user"""
        investigation_id = self.request.query_params.get('investigation_id')
        queryset = SubTask.objects.filter(
            investigation__user=self.request.user
        )
        
        if investigation_id:
            queryset = queryset.filter(investigation_id=investigation_id)
        
        return queryset.order_by('order')