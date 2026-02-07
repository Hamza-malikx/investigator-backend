# entities/serializers.py
from rest_framework import serializers
from .models import Entity, Relationship


class EntitySerializer(serializers.ModelSerializer):
    """Serializer for Entity model"""
    relationships_count = serializers.SerializerMethodField()
    evidence_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Entity
        fields = [
            'id', 'investigation', 'entity_type', 'name', 'aliases',
            'description', 'confidence', 'source_count', 'metadata',
            'position_x', 'position_y', 'discovered_by_task',
            'relationships_count', 'evidence_count', 'created_at'
        ]
        read_only_fields = ['id', 'discovered_by_task', 'created_at']
    
    def get_relationships_count(self, obj):
        return obj.outgoing_relationships.count() + obj.incoming_relationships.count()
    
    def get_evidence_count(self, obj):
        return obj.evidence_links.count()


class EntityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing entities"""
    
    class Meta:
        model = Entity
        fields = [
            'id', 'entity_type', 'name', 'confidence',
            'source_count', 'position_x', 'position_y'
        ]


class RelationshipSerializer(serializers.ModelSerializer):
    """Serializer for Relationship model"""
    source_entity_name = serializers.CharField(source='source_entity.name', read_only=True)
    target_entity_name = serializers.CharField(source='target_entity.name', read_only=True)
    source_entity_type = serializers.CharField(source='source_entity.entity_type', read_only=True)
    target_entity_type = serializers.CharField(source='target_entity.entity_type', read_only=True)
    evidence_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Relationship
        fields = [
            'id', 'investigation', 'source_entity', 'target_entity',
            'source_entity_name', 'target_entity_name',
            'source_entity_type', 'target_entity_type',
            'relationship_type', 'description', 'confidence', 'strength',
            'start_date', 'end_date', 'is_active',
            'discovered_by_task', 'evidence_count', 'created_at'
        ]
        read_only_fields = ['id', 'discovered_by_task', 'created_at']
    
    def get_evidence_count(self, obj):
        return obj.evidence_links.count()


class RelationshipListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing relationships"""
    
    class Meta:
        model = Relationship
        fields = [
            'id', 'source_entity', 'target_entity', 'relationship_type',
            'confidence', 'strength', 'is_active'
        ]


class EntityWithRelationshipsSerializer(serializers.ModelSerializer):
    """Entity with all its relationships"""
    outgoing_relationships = RelationshipListSerializer(many=True, read_only=True)
    incoming_relationships = RelationshipListSerializer(many=True, read_only=True)
    
    class Meta:
        model = Entity
        fields = [
            'id', 'entity_type', 'name', 'description', 'confidence',
            'metadata', 'outgoing_relationships', 'incoming_relationships'
        ]


class EntityAnnotationSerializer(serializers.Serializer):
    """Serializer for user annotations on entities"""
    note = serializers.CharField(max_length=1000)
    entity_id = serializers.UUIDField()