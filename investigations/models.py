from django.db import models
from django.conf import settings
import uuid

class Investigation(models.Model):
    """Main investigation entity"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='investigations')
    
    # Basic info
    title = models.CharField(max_length=200)
    initial_query = models.TextField(help_text="Original research question")
    
    # Status tracking
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    PHASE_CHOICES = [
        ('planning', 'Planning'),
        ('researching', 'Researching'),
        ('analyzing', 'Analyzing'),
        ('reporting', 'Reporting'),
    ]
    current_phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default='planning')
    
    # Progress metrics
    progress_percentage = models.IntegerField(default=0)
    confidence_score = models.FloatField(default=0.0)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_completion = models.DateTimeField(null=True, blank=True)
    
    # Resource tracking
    total_api_calls = models.IntegerField(default=0)
    total_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'investigations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'current_phase']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.status}"


class InvestigationPlan(models.Model):
    """Research strategy for an investigation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.OneToOneField(Investigation, on_delete=models.CASCADE, related_name='plan')
    
    research_strategy = models.JSONField(default=list, help_text="List of planned research steps")
    hypothesis = models.TextField(blank=True)
    priority_areas = models.JSONField(default=list)
    avoided_paths = models.JSONField(default=list, help_text="Dead ends to skip")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'investigation_plans'
    
    def __str__(self):
        return f"Plan for {self.investigation.title}"


class SubTask(models.Model):
    """Individual research tasks"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE, related_name='subtasks')
    parent_task = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    
    TASK_TYPE_CHOICES = [
        ('web_search', 'Web Search'),
        ('document_analysis', 'Document Analysis'),
        ('entity_extraction', 'Entity Extraction'),
        ('relationship_mapping', 'Relationship Mapping'),
    ]
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES)
    description = models.TextField()
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    result = models.JSONField(null=True, blank=True)
    confidence = models.FloatField(default=0.0)
    order = models.IntegerField(default=0)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'subtasks'
        ordering = ['order']
        indexes = [
            models.Index(fields=['investigation', 'status']),
        ]
    
    def __str__(self):
        return f"{self.task_type}: {self.description[:50]}"