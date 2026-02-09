# agents/views.py - UPDATED with automatic layout

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import networkx as nx
from typing import Dict, List, Tuple

from agents.models import ThoughtChain, AgentDecision
from investigations.models import Investigation
from entities.models import Entity, Relationship
from evidence.models import Evidence
from agents.serializers import (
    ThoughtChainSerializer, AgentDecisionSerializer, BoardStateSerializer
)


class ThoughtChainViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ThoughtChain (read-only).
    Shows agent's reasoning process.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ThoughtChainSerializer
    
    def get_queryset(self):
        """Filter by investigation and user"""
        investigation_id = self.kwargs.get('investigation_pk')
        
        if investigation_id:
            return ThoughtChain.objects.filter(
                investigation_id=investigation_id,
                investigation__user=self.request.user
            ).select_related('investigation', 'parent_thought', 'led_to_task')
        
        queryset = ThoughtChain.objects.filter(
            investigation__user=self.request.user
        ).select_related('investigation', 'parent_thought', 'led_to_task')
        
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
        
        investigation_id = self.request.query_params.get('investigation_id')
        if investigation_id:
            queryset = queryset.filter(investigation_id=investigation_id)
        
        return queryset


class BoardViewSet(viewsets.ViewSet):
    """
    ViewSet for investigation board visualization.
    Returns graph data (nodes and edges) for React Flow with automatic layout.
    
    Endpoints:
    - GET /api/v1/investigations/{id}/board/ - Get board state with auto-layout
    - GET /api/v1/investigations/{id}/board/stats/ - Get statistics
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request, investigation_pk=None):
        """
        Get complete board state with automatic graph layout.
        
        Uses NetworkX for intelligent node positioning when positions aren't saved.
        """
        # Verify user has access
        investigation = get_object_or_404(
            Investigation,
            id=investigation_pk,
            user=request.user
        )
        
        # Get layout type from query params
        layout_type = request.query_params.get('layout', 'spring')
        
        # Get all entities and relationships
        entities = list(Entity.objects.filter(investigation=investigation).select_related('investigation'))
        relationships = list(Relationship.objects.filter(
            investigation=investigation
        ).select_related('source_entity', 'target_entity'))
        
        # Calculate positions using NetworkX if not already set
        positions = self._calculate_layout(entities, relationships, layout_type)
        
        # Build nodes array
        nodes = []
        for entity in entities:
            entity_id = str(entity.id)
            
            # Count relationships
            relationships_count = sum(
                1 for r in relationships 
                if str(r.source_entity.id) == entity_id or str(r.target_entity.id) == entity_id
            )
            
            # Get aliases from metadata
            aliases = entity.metadata.get('aliases', []) if entity.metadata else []
            
            # Get position (from calculated layout or saved position)
            position = positions.get(entity_id, {'x': 0, 'y': 0})
            
            nodes.append({
                'id': entity_id,
                'name': entity.name,
                'type': entity.entity_type,
                'description': entity.description or '',
                'confidence': float(entity.confidence),
                'source_count': entity.source_count,
                'relationships_count': relationships_count,
                'aliases': aliases,
                'position': position,
                'color': self._get_entity_color(entity.entity_type),
                'size': self._calculate_node_size(entity, relationships_count),
            })
        
        # Build edges array
        edges = []
        for rel in relationships:
            edges.append({
                'id': str(rel.id),
                'source': str(rel.source_entity.id),
                'target': str(rel.target_entity.id),
                'type': rel.relationship_type,
                'label': rel.description or rel.relationship_type.replace('_', ' ').title(),
                'confidence': float(rel.confidence),
                'strength': float(rel.strength),
                'is_active': rel.is_active,
                'style': 'solid' if rel.confidence > 0.7 else 'dashed',
                'width': max(2, min(6, int(rel.strength * 5))),
            })
        
        return Response({
            'investigation_id': str(investigation.id),
            'status': investigation.status,
            'nodes': nodes,
            'edges': edges,
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'layout_type': layout_type
        })
    
    def _calculate_layout(
        self, 
        entities: List[Entity], 
        relationships: List[Relationship],
        layout_type: str = 'spring'
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate node positions using NetworkX graph layout algorithms.
        
        Args:
            entities: List of Entity objects
            relationships: List of Relationship objects
            layout_type: 'spring', 'circular', 'hierarchical', 'grid', or 'type'
        
        Returns:
            Dictionary mapping entity_id to {x, y} positions
        """
        # Check if entities have saved positions
        has_saved_positions = any(
            e.position_x is not None and e.position_y is not None 
            for e in entities
        )
        
        if has_saved_positions:
            # Use saved positions
            return {
                str(e.id): {
                    'x': e.position_x if e.position_x is not None else 0,
                    'y': e.position_y if e.position_y is not None else 0
                }
                for e in entities
            }
        
        # No saved positions - calculate layout
        if not entities:
            return {}
        
        # Build NetworkX graph
        G = nx.Graph()
        
        # Add nodes
        for entity in entities:
            G.add_node(str(entity.id), entity_type=entity.entity_type)
        
        # Add edges
        for rel in relationships:
            G.add_edge(
                str(rel.source_entity.id),
                str(rel.target_entity.id),
                weight=float(rel.strength)
            )
        
        # Calculate layout based on type
        if layout_type == 'spring':
            # Force-directed layout (best for most graphs)
            pos = nx.spring_layout(G, k=2, iterations=50, scale=1000, center=(500, 400))
        
        elif layout_type == 'circular':
            # Circular layout
            pos = nx.circular_layout(G, scale=600, center=(600, 400))
        
        elif layout_type == 'hierarchical':
            # Hierarchical layout (tries to detect hierarchy)
            try:
                pos = nx.kamada_kawai_layout(G, scale=800, center=(500, 400))
            except:
                # Fallback to spring if hierarchical fails
                pos = nx.spring_layout(G, k=2, iterations=50, scale=1000, center=(500, 400))
        
        elif layout_type == 'grid':
            # Grid layout
            import math
            n = len(entities)
            cols = math.ceil(math.sqrt(n))
            
            pos = {}
            for idx, entity in enumerate(entities):
                row = idx // cols
                col = idx % cols
                pos[str(entity.id)] = (100 + col * 350, 100 + row * 250)
        
        elif layout_type == 'type':
            # Group by entity type
            type_groups = {}
            for entity in entities:
                entity_type = entity.entity_type
                if entity_type not in type_groups:
                    type_groups[entity_type] = []
                type_groups[entity_type].append(entity)
            
            pos = {}
            type_x = 100
            for entity_type, group in type_groups.items():
                for idx, entity in enumerate(group):
                    pos[str(entity.id)] = (type_x, 100 + idx * 200)
                type_x += 400
        
        else:
            # Default to spring layout
            pos = nx.spring_layout(G, k=2, iterations=50, scale=1000, center=(500, 400))
        
        # Convert to our format
        positions = {}
        for entity_id, (x, y) in pos.items():
            positions[entity_id] = {
                'x': float(x),
                'y': float(y)
            }
        
        return positions
    
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
        evidence = Evidence.objects.filter(investigation=investigation)
        
        # Entity type breakdown
        entity_breakdown = {}
        entity_list = list(entities)
        for entity in entity_list:
            entity_type = entity.entity_type
            entity_breakdown[entity_type] = entity_breakdown.get(entity_type, 0) + 1
        
        # Relationship type breakdown
        relationship_breakdown = {}
        relationship_list = list(relationships)
        for rel in relationship_list:
            rel_type = rel.relationship_type
            relationship_breakdown[rel_type] = relationship_breakdown.get(rel_type, 0) + 1
        
        # Confidence stats
        avg_entity_confidence = (
            sum(e.confidence for e in entity_list) / len(entity_list) 
            if entity_list else 0
        )
        avg_rel_confidence = (
            sum(r.confidence for r in relationship_list) / len(relationship_list) 
            if relationship_list else 0
        )
        
        return Response({
            'investigation_id': str(investigation.id),
            'total_entities': len(entity_list),
            'total_relationships': len(relationship_list),
            'total_evidence': evidence.count(),
            'average_confidence': round((avg_entity_confidence + avg_rel_confidence) / 2, 2) if (entity_list or relationship_list) else 0,
            'entity_breakdown': entity_breakdown,
            'relationship_breakdown': relationship_breakdown,
            'avg_entity_confidence': round(avg_entity_confidence, 2),
            'avg_relationship_confidence': round(avg_rel_confidence, 2),
        })
    
    @action(detail=False, methods=['post'])
    def update_positions(self, request, investigation_pk=None):
        """
        Update entity positions for layout persistence.
        
        Body: { "nodes": [{ "id": "uuid", "x": 100, "y": 200 }] }
        """
        investigation = get_object_or_404(
            Investigation,
            id=investigation_pk,
            user=request.user
        )
        
        nodes_data = request.data.get('nodes', [])
        
        updated_count = 0
        for node_data in nodes_data:
            entity_id = node_data.get('id')
            x = node_data.get('x')
            y = node_data.get('y')
            
            if entity_id and x is not None and y is not None:
                try:
                    entity = Entity.objects.get(
                        id=entity_id,
                        investigation=investigation
                    )
                    entity.position_x = x
                    entity.position_y = y
                    entity.save(update_fields=['position_x', 'position_y'])
                    updated_count += 1
                except Entity.DoesNotExist:
                    continue
        
        return Response({
            'message': f'Updated {updated_count} entity positions',
            'updated_count': updated_count
        })
    
    # Helper methods
    
    def _get_entity_color(self, entity_type: str) -> str:
        """Get color for entity type (matches frontend theme)"""
        color_map = {
            'person': '#6366f1',           # Indigo
            'company': '#8b5cf6',          # Purple
            'location': '#10b981',         # Green
            'event': '#f59e0b',            # Amber
            'document': '#3b82f6',         # Blue
            'financial_instrument': '#14b8a6',  # Teal
        }
        return color_map.get(entity_type, '#6b7280')  # Gray default
    
    def _calculate_node_size(self, entity: Entity, relationships_count: int) -> int:
        """Calculate node size based on importance"""
        base_size = 20
        
        size = base_size + (relationships_count * 3) + (entity.source_count * 2)
        size = int(size * entity.confidence)
        
        return max(20, min(100, size))