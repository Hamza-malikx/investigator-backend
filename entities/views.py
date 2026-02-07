# entities/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Entity, Relationship
from .serializers import (
    EntitySerializer, EntityListSerializer, EntityWithRelationshipsSerializer,
    RelationshipSerializer, RelationshipListSerializer, EntityAnnotationSerializer
)


class EntityViewSet(viewsets.ModelViewSet):
    """ViewSet for Entity CRUD operations"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter entities by investigation and user"""
        investigation_id = self.kwargs.get('investigation_pk')
        
        if investigation_id:
            return Entity.objects.filter(
                investigation_id=investigation_id,
                investigation__user=self.request.user
            ).select_related('investigation', 'discovered_by_task')
        
        return Entity.objects.filter(
            investigation__user=self.request.user
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EntityListSerializer
        return EntitySerializer
    
    @action(detail=True, methods=['get'])
    def relationships(self, request, investigation_pk=None, pk=None):
        """Get all relationships for an entity"""
        entity = self.get_object()
        
        outgoing = entity.outgoing_relationships.all()
        incoming = entity.incoming_relationships.all()
        
        return Response({
            'entity_id': str(entity.id),
            'entity_name': entity.name,
            'outgoing_relationships': RelationshipListSerializer(outgoing, many=True).data,
            'incoming_relationships': RelationshipListSerializer(incoming, many=True).data,
            'total_relationships': outgoing.count() + incoming.count()
        })
    
    @action(detail=True, methods=['get'])
    def evidence(self, request, investigation_pk=None, pk=None):
        """Get all evidence mentioning this entity"""
        entity = self.get_object()
        evidence_links = entity.evidence_links.select_related('evidence').all()
        
        from evidence.serializers import EvidenceListSerializer
        
        evidence_data = []
        for link in evidence_links:
            evidence_data.append({
                'evidence': EvidenceListSerializer(link.evidence).data,
                'relevance': link.relevance,
                'quote': link.quote
            })
        
        return Response({
            'entity_id': str(entity.id),
            'entity_name': entity.name,
            'evidence': evidence_data,
            'total_evidence': len(evidence_data)
        })
    
    @action(detail=True, methods=['post'])
    def annotate(self, request, investigation_pk=None, pk=None):
        """Add user annotation to entity"""
        entity = self.get_object()
        serializer = EntityAnnotationSerializer(data=request.data)
        
        if serializer.is_valid():
            # TODO: Implement board annotations
            # For now, just return success
            return Response({
                'message': 'Annotation added successfully',
                'entity_id': str(entity.id),
                'note': serializer.validated_data['note']
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RelationshipViewSet(viewsets.ModelViewSet):
    """ViewSet for Relationship CRUD operations"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter relationships by investigation and user"""
        investigation_id = self.kwargs.get('investigation_pk')
        
        if investigation_id:
            return Relationship.objects.filter(
                investigation_id=investigation_id,
                investigation__user=self.request.user
            ).select_related('source_entity', 'target_entity', 'investigation')
        
        return Relationship.objects.filter(
            investigation__user=self.request.user
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RelationshipListSerializer
        return RelationshipSerializer
    
    @action(detail=True, methods=['get'])
    def evidence(self, request, investigation_pk=None, pk=None):
        """Get supporting/contradicting evidence for relationship"""
        relationship = self.get_object()
        evidence_links = relationship.evidence_links.select_related('evidence').all()
        
        from evidence.serializers import EvidenceListSerializer
        
        supporting = []
        contradicting = []
        
        for link in evidence_links:
            evidence_item = {
                'evidence': EvidenceListSerializer(link.evidence).data,
                'strength': link.strength,
                'quote': link.quote
            }
            
            if link.supports:
                supporting.append(evidence_item)
            else:
                contradicting.append(evidence_item)
        
        return Response({
            'relationship_id': str(relationship.id),
            'relationship_type': relationship.relationship_type,
            'source': relationship.source_entity.name,
            'target': relationship.target_entity.name,
            'supporting_evidence': supporting,
            'contradicting_evidence': contradicting,
            'net_confidence': relationship.confidence
        })
    
    @action(detail=True, methods=['patch'])
    def confidence(self, request, investigation_pk=None, pk=None):
        """Update relationship confidence (user override)"""
        relationship = self.get_object()
        confidence = request.data.get('confidence')
        
        if confidence is None or not (0 <= float(confidence) <= 1):
            return Response(
                {'error': 'Confidence must be between 0 and 1'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        relationship.confidence = float(confidence)
        relationship.save()
        
        return Response({
            'message': 'Confidence updated',
            'relationship_id': str(relationship.id),
            'new_confidence': relationship.confidence
        })