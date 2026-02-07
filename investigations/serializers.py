# investigations/serializers.py

from rest_framework import serializers
from .models import Investigation, InvestigationPlan, SubTask
from django.contrib.auth import get_user_model

User = get_user_model()


class SubTaskSerializer(serializers.ModelSerializer):
    """Serializer for SubTask model"""
    
    class Meta:
        model = SubTask
        fields = [
            'id', 'investigation', 'parent_task', 'task_type',
            'description', 'status', 'result', 'confidence',
            'order', 'started_at', 'completed_at'
        ]
        read_only_fields = ['id', 'started_at', 'completed_at']


class InvestigationPlanSerializer(serializers.ModelSerializer):
    """Serializer for InvestigationPlan model"""
    
    class Meta:
        model = InvestigationPlan
        fields = [
            'id', 'investigation', 'research_strategy', 'hypothesis',
            'priority_areas', 'avoided_paths', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvestigationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing investigations"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    entities_count = serializers.SerializerMethodField()
    relationships_count = serializers.SerializerMethodField()
    evidence_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Investigation
        fields = [
            'id', 'user_email', 'title', 'status', 'current_phase',
            'progress_percentage', 'confidence_score',
            'entities_count', 'relationships_count', 'evidence_count',
            'started_at', 'estimated_completion', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_entities_count(self, obj):
        return obj.entities.count()
    
    def get_relationships_count(self, obj):
        return obj.relationships.count()
    
    def get_evidence_count(self, obj):
        return obj.evidence.count()


class InvestigationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for investigation with nested data"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    plan = InvestigationPlanSerializer(read_only=True)
    subtasks = SubTaskSerializer(many=True, read_only=True)
    entities_count = serializers.SerializerMethodField()
    relationships_count = serializers.SerializerMethodField()
    evidence_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Investigation
        fields = [
            'id', 'user', 'user_email', 'title', 'initial_query',
            'status', 'current_phase', 'progress_percentage', 'confidence_score',
            'started_at', 'completed_at', 'estimated_completion',
            'total_api_calls', 'total_cost_usd',
            'plan', 'subtasks',
            'entities_count', 'relationships_count', 'evidence_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'started_at', 'completed_at',
            'total_api_calls', 'total_cost_usd', 'created_at', 'updated_at'
        ]
    
    def get_entities_count(self, obj):
        return obj.entities.count()
    
    def get_relationships_count(self, obj):
        return obj.relationships.count()
    
    def get_evidence_count(self, obj):
        return obj.evidence.count()


class InvestigationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new investigations"""
    focus_areas = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="Areas to focus the investigation on"
    )
    depth_level = serializers.ChoiceField(
        choices=['shallow', 'moderate', 'comprehensive'],
        default='moderate',
        help_text="How deep the investigation should go"
    )
    time_range = serializers.JSONField(
        required=False,
        help_text="Time range for investigation (start and end dates)"
    )
    
    class Meta:
        model = Investigation
        fields = ['title', 'initial_query', 'focus_areas', 'depth_level', 'time_range']
    
    def create(self, validated_data):
        # Extract extra fields that aren't in the model
        focus_areas = validated_data.pop('focus_areas', [])
        depth_level = validated_data.pop('depth_level', 'moderate')
        time_range = validated_data.pop('time_range', {})
        
        # Create investigation
        investigation = Investigation.objects.create(
            user=self.context['request'].user,
            **validated_data
        )
        
        # Create investigation plan with the extra data
        InvestigationPlan.objects.create(
            investigation=investigation,
            priority_areas=focus_areas,
            research_strategy=[
                {
                    'depth': depth_level,
                    'time_range': time_range,
                    'created_at': str(investigation.created_at)
                }
            ]
        )
        
        return investigation


class InvestigationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating investigation status"""
    
    class Meta:
        model = Investigation
        fields = ['status', 'current_phase']
    
    def validate_status(self, value):
        """Ensure valid status transitions"""
        current_status = self.instance.status if self.instance else None
        
        # Define valid transitions
        valid_transitions = {
            'pending': ['running', 'failed'],
            'running': ['paused', 'completed', 'failed'],
            'paused': ['running', 'failed'],
            'completed': [],
            'failed': []
        }
        
        if current_status and value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot transition from {current_status} to {value}"
            )
        
        return value


class InvestigationRedirectSerializer(serializers.Serializer):
    """Serializer for redirecting investigation focus"""
    focus = serializers.CharField(
        required=True,
        help_text="New focus for the investigation"
    )
    priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high'],
        default='medium'
    )