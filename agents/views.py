from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from agents.models import ThoughtChain, AgentDecision
from investigations.models import Investigation
from entities.models import Entity, Relationship
from agents.serializers import (
    ThoughtChainSerializer, AgentDecisionSerializer, BoardStateSerializer
)


class ThoughtChainViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ThoughtChain (read-only).
    Shows agent's reasoning process.
    
    Can be accessed via:
    - /api/v1/agents/thoughts/
    - /api/v1/investigations/{id}/thoughts/ (if nested)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ThoughtChainSerializer
    
    def get_queryset(self):
        """Filter by investigation and user"""
        # Check if we're in a nested route (under investigations)
        investigation_id = self.kwargs.get('investigation_pk')
        
        if investigation_id:
            # Nested route: filter by specific investigation
            return ThoughtChain.objects.filter(
                investigation_id=investigation_id,
                investigation__user=self.request.user
            ).select_related('investigation', 'parent_thought', 'led_to_task')
        
        # Standalone route: filter by query params
        queryset = ThoughtChain.objects.filter(
            investigation__user=self.request.user
        ).select_related('investigation', 'parent_thought', 'led_to_task')
        
        # Filter by investigation if provided in query params
        investigation_id = self.request.query_params.get('investigation_id')
        if investigation_id:
            queryset = queryset.filter(investigation_id=investigation_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def timeline(self, request, investigation_pk=None):
        """Get thought chain as a timeline"""
        thoughts = self.get_queryset().order_by('sequence_number', 'timestamp')
        
        timeline = []
        for thought in thoughts:
            timeline.append({
                'id': str(thought.id),
                'sequence': thought.sequence_number,
                'type': thought.thought_type,
                'content': thought.content,
                'confidence_before': thought.confidence_before,
                'confidence_after': thought.confidence_after,
                'timestamp': thought.timestamp.isoformat(),
                'parent_id': str(thought.parent_thought.id) if thought.parent_thought else None
            })
        
        return Response({
            'investigation_id': investigation_pk or request.query_params.get('investigation_id'),
            'total_thoughts': len(timeline),
            'timeline': timeline
        })


class AgentDecisionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AgentDecision (read-only).
    Shows major decision points.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgentDecisionSerializer
    
    def get_queryset(self):
        """Filter by investigation and user"""
        investigation_id = self.kwargs.get('investigation_pk')
        
        if investigation_id:
            return AgentDecision.objects.filter(
                investigation_id=investigation_id,
                investigation__user=self.request.user
            )
        
        queryset = AgentDecision.objects.filter(
            investigation__user=self.request.user
        )
        
        # Filter by investigation if provided in query params
        investigation_id = self.request.query_params.get('investigation_id')
        if investigation_id:
            queryset = queryset.filter(investigation_id=investigation_id)
        
        return queryset


class BoardViewSet(viewsets.ViewSet):
    """
    ViewSet for investigation board visualization.
    Returns graph data (nodes and edges).
    
    Accessed via: /api/v1/investigations/{id}/board/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def retrieve(self, request, investigation_pk=None):
        """
        Get complete board state for an investigation.
        
        Returns:
        {
            "investigation_id": "uuid",
            "nodes": [...],  // Entities as graph nodes
            "edges": [...],  // Relationships as graph edges
            "total_nodes": 10,
            "total_edges": 15,
            "layout_type": "force_directed"
        }
        """
        # Verify user has access
        investigation = get_object_or_404(
            Investigation,
            id=investigation_pk,
            user=request.user
        )
        
        # Get entities (nodes)
        entities = Entity.objects.filter(investigation=investigation)
        
        nodes = []
        for entity in entities:
            nodes.append({
                'id': str(entity.id),
                'type': entity.entity_type,
                'label': entity.name,
                'description': entity.description,
                'confidence': entity.confidence,
                'source_count': entity.source_count,
                'position': {
                    'x': entity.position_x or 0,
                    'y': entity.position_y or 0
                },
                'metadata': entity.metadata,
                # Visual properties
                'color': self._get_entity_color(entity.entity_type),
                'size': self._calculate_node_size(entity),
            })
        
        # Get relationships (edges)
        relationships = Relationship.objects.filter(
            investigation=investigation
        ).select_related('source_entity', 'target_entity')
        
        edges = []
        for rel in relationships:
            edges.append({
                'id': str(rel.id),
                'source': str(rel.source_entity.id),
                'target': str(rel.target_entity.id),
                'type': rel.relationship_type,
                'label': rel.description or rel.relationship_type.replace('_', ' ').title(),
                'confidence': rel.confidence,
                'strength': rel.strength,
                'is_active': rel.is_active,
                # Visual properties
                'style': 'solid' if rel.confidence > 0.7 else 'dashed',
                'width': int(rel.strength * 5) + 1,  # 1-6 pixels
            })
        
        data = {
            'investigation_id': str(investigation.id),
            'nodes': nodes,
            'edges': edges,
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'layout_type': 'force_directed'
        }
        
        serializer = BoardStateSerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request, investigation_pk=None):
        """Get board statistics"""
        investigation = get_object_or_404(
            Investigation,
            id=investigation_pk,
            user=request.user
        )
        
        entities = Entity.objects.filter(investigation=investigation)
        relationships = Relationship.objects.filter(investigation=investigation)
        
        # Entity type breakdown
        entity_breakdown = {}
        for entity in entities:
            entity_type = entity.entity_type
            entity_breakdown[entity_type] = entity_breakdown.get(entity_type, 0) + 1
        
        # Relationship type breakdown
        relationship_breakdown = {}
        for rel in relationships:
            rel_type = rel.relationship_type
            relationship_breakdown[rel_type] = relationship_breakdown.get(rel_type, 0) + 1
        
        # Confidence stats
        avg_entity_confidence = sum(e.confidence for e in entities) / len(entities) if entities else 0
        avg_rel_confidence = sum(r.confidence for r in relationships) / len(relationships) if relationships else 0
        
        return Response({
            'investigation_id': str(investigation.id),
            'total_entities': entities.count(),
            'total_relationships': relationships.count(),
            'entity_breakdown': entity_breakdown,
            'relationship_breakdown': relationship_breakdown,
            'avg_entity_confidence': round(avg_entity_confidence, 2),
            'avg_relationship_confidence': round(avg_rel_confidence, 2),
        })
    
    # Helper methods
    
    def _get_entity_color(self, entity_type: str) -> str:
        """Get color for entity type"""
        color_map = {
            'person': '#3B82F6',      # Blue
            'company': '#10B981',      # Green
            'location': '#F59E0B',     # Orange
            'event': '#EF4444',        # Red
            'document': '#8B5CF6',     # Purple
            'financial_instrument': '#EC4899',  # Pink
        }
        return color_map.get(entity_type, '#6B7280')  # Gray default
    
    def _calculate_node_size(self, entity: Entity) -> int:
        """Calculate node size based on importance"""
        # Base size
        base_size = 20
        
        # Increase size based on:
        # - Number of relationships
        relationship_count = (
            entity.outgoing_relationships.count() + 
            entity.incoming_relationships.count()
        )
        
        # - Source count
        # - Confidence
        
        size = base_size + (relationship_count * 3) + (entity.source_count * 2)
        size = int(size * entity.confidence)
        
        # Cap at 100
        return min(size, 100)