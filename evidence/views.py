from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Evidence
from .serializers import (
    EvidenceSerializer, EvidenceListSerializer, EvidenceUploadSerializer
)


class EvidenceViewSet(viewsets.ModelViewSet):
    """ViewSet for Evidence CRUD operations"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Filter evidence by investigation and user"""
        investigation_id = self.kwargs.get('investigation_pk')
        
        if investigation_id:
            return Evidence.objects.filter(
                investigation_id=investigation_id,
                investigation__user=self.request.user
            ).select_related('investigation')
        
        return Evidence.objects.filter(
            investigation__user=self.request.user
        )
    
    def get_serializer_class(self):
        if self.action == 'upload':
            return EvidenceUploadSerializer
        elif self.action == 'list':
            return EvidenceListSerializer
        return EvidenceSerializer
    
    @action(detail=False, methods=['post'])
    def upload(self, request, investigation_pk=None):
        """Upload document for analysis"""
        serializer = EvidenceUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            evidence = serializer.save()
            
            # TODO: Trigger Celery task to analyze document
            # from .tasks import analyze_document
            # analyze_document.delay(evidence.id)
            
            return Response({
                'evidence_id': str(evidence.id),
                'status': 'processing',
                'message': 'Document uploaded successfully and queued for analysis',
                'estimated_analysis_time': 120  # seconds
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def content(self, request, investigation_pk=None, pk=None):
        """Get full extracted content of evidence"""
        evidence = self.get_object()
        
        return Response({
            'evidence_id': str(evidence.id),
            'title': evidence.title,
            'evidence_type': evidence.evidence_type,
            'content': evidence.content,
            'source_url': evidence.source_url,
            'source_credibility': evidence.source_credibility,
            'metadata': evidence.metadata,
            'created_at': evidence.created_at
        })