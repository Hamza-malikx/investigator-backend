from rest_framework import serializers
from agents.models import ThoughtChain, AgentDecision


class ThoughtChainSerializer(serializers.ModelSerializer):
    """Serializer for ThoughtChain model"""
    parent_thought_id = serializers.UUIDField(source='parent_thought.id', read_only=True, allow_null=True)
    led_to_task_id = serializers.UUIDField(source='led_to_task.id', read_only=True, allow_null=True)
    
    class Meta:
        model = ThoughtChain
        fields = [
            'id', 'investigation', 'sequence_number', 'thought_type',
            'content', 'parent_thought_id', 'led_to_task_id',
            'confidence_before', 'confidence_after', 'timestamp'
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
    """Serializer for complete board state (graph visualization)"""
    investigation_id = serializers.UUIDField()
    nodes = serializers.ListField(child=serializers.DictField())
    edges = serializers.ListField(child=serializers.DictField())
    total_nodes = serializers.IntegerField()
    total_edges = serializers.IntegerField()
    layout_type = serializers.CharField(default='force_directed')