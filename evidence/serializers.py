from rest_framework import serializers
from .models import Evidence, EvidenceEntityLink, EvidenceRelationshipLink


class EvidenceEntityLinkSerializer(serializers.ModelSerializer):
    """Serializer for evidence-entity links"""
    entity_name = serializers.CharField(source='entity.name', read_only=True)
    entity_type = serializers.CharField(source='entity.entity_type', read_only=True)
    
    class Meta:
        model = EvidenceEntityLink
        fields = ['id', 'entity', 'entity_name', 'entity_type', 'relevance', 'quote']


class EvidenceRelationshipLinkSerializer(serializers.ModelSerializer):
    """Serializer for evidence-relationship links"""
    relationship_type = serializers.CharField(source='relationship.relationship_type', read_only=True)
    source_name = serializers.CharField(source='relationship.source_entity.name', read_only=True)
    target_name = serializers.CharField(source='relationship.target_entity.name', read_only=True)
    
    class Meta:
        model = EvidenceRelationshipLink
        fields = [
            'id', 'relationship', 'relationship_type',
            'source_name', 'target_name', 'supports', 'strength', 'quote'
        ]


class EvidenceSerializer(serializers.ModelSerializer):
    """Serializer for Evidence model"""
    entity_links = EvidenceEntityLinkSerializer(many=True, read_only=True)
    relationship_links = EvidenceRelationshipLinkSerializer(many=True, read_only=True)
    
    class Meta:
        model = Evidence
        fields = [
            'id', 'investigation', 'evidence_type', 'title', 'content',
            'source_url', 'source_credibility', 'file_path', 'file_type',
            'metadata', 'discovered_by_task', 'entity_links',
            'relationship_links', 'created_at'
        ]
        read_only_fields = ['id', 'discovered_by_task', 'created_at']


class EvidenceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing evidence"""
    
    class Meta:
        model = Evidence
        fields = [
            'id', 'evidence_type', 'title', 'source_url',
            'source_credibility', 'created_at'
        ]


class EvidenceUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading evidence documents"""
    file = serializers.FileField(write_only=True)
    source = serializers.CharField(max_length=200, required=False)
    
    class Meta:
        model = Evidence
        fields = ['investigation', 'title', 'file', 'source', 'evidence_type']
    
    def create(self, validated_data):
        file = validated_data.pop('file')
        source = validated_data.pop('source', '')
        
        evidence = Evidence.objects.create(
            file_path=file,
            file_type=file.content_type,
            metadata={'source': source, 'original_filename': file.name},
            **validated_data
        )
        
        return evidence