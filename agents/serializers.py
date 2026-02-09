# agents/serializers.py

from rest_framework import serializers
from .models import ThoughtChain, AgentDecision


class ThoughtChainSerializer(serializers.ModelSerializer):
    """Serializer for ThoughtChain model"""
    parent_thought_id = serializers.UUIDField(source='parent_thought.id', read_only=True, allow_null=True)
    led_to_task_id = serializers.UUIDField(source='led_to_task.id', read_only=True, allow_null=True)
    
    class Meta:
        model = ThoughtChain
        fields = [
            'id', 'investigation', 'sequence_number', 'thought_type',
            'content', 'parent_thought', 'parent_thought_id',
            'led_to_task', 'led_to_task_id', 'confidence_before',
            'confidence_after', 'gemini_thought_signature', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class AgentDecisionSerializer(serializers.ModelSerializer):
    """Serializer for AgentDecision model"""
    
    class Meta:
        model = AgentDecision
        fields = [
            'id', 'investigation', 'decision_point', 'options_considered',
            'chosen_option', 'reasoning', 'outcome', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class BoardStateSerializer(serializers.Serializer):
    """Serializer for board visualization state"""
    investigation_id = serializers.UUIDField()
    status = serializers.CharField(required=False)
    nodes = serializers.ListField(child=serializers.DictField())
    edges = serializers.ListField(child=serializers.DictField())
    total_nodes = serializers.IntegerField()
    total_edges = serializers.IntegerField()
    layout_type = serializers.CharField(default='force_directed')


class BoardStatsSerializer(serializers.Serializer):
    """Serializer for board statistics"""
    investigation_id = serializers.UUIDField()
    total_entities = serializers.IntegerField()
    total_relationships = serializers.IntegerField()
    total_evidence = serializers.IntegerField()
    average_confidence = serializers.FloatField()
    entity_breakdown = serializers.DictField()
    relationship_breakdown = serializers.DictField()
    avg_entity_confidence = serializers.FloatField()
    avg_relationship_confidence = serializers.FloatField()