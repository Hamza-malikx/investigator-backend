from django.db import models
import uuid


class ThoughtChain(models.Model):
    """
    Agent's thought process for transparency.
    Shows how the AI reasons through the investigation.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.ForeignKey(
        'investigations.Investigation',
        on_delete=models.CASCADE,
        related_name='thoughts'
    )
    
    sequence_number = models.IntegerField(help_text="Order in the thought chain")
    
    THOUGHT_TYPE_CHOICES = [
        ('hypothesis', 'Hypothesis'),
        ('question', 'Question'),
        ('observation', 'Observation'),
        ('conclusion', 'Conclusion'),
        ('correction', 'Correction'),
    ]
    thought_type = models.CharField(max_length=20, choices=THOUGHT_TYPE_CHOICES)
    
    content = models.TextField(help_text="The actual thought/reasoning")
    
    # Optional links
    parent_thought = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='child_thoughts'
    )
    led_to_task = models.ForeignKey(
        'investigations.SubTask',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='thoughts'
    )
    
    # Confidence tracking
    confidence_before = models.FloatField(default=0.5)
    confidence_after = models.FloatField(default=0.5)
    
    # For Gemini continuity
    gemini_thought_signature = models.TextField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'thought_chains'
        ordering = ['sequence_number', 'timestamp']
        indexes = [
            models.Index(fields=['investigation', 'sequence_number']),
            models.Index(fields=['investigation', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.thought_type}: {self.content[:50]}"


class AgentDecision(models.Model):
    """
    Major decision points in the investigation.
    Records when the agent makes strategic choices.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.ForeignKey(
        'investigations.Investigation',
        on_delete=models.CASCADE,
        related_name='decisions'
    )
    
    decision_point = models.TextField(help_text="What decision was being made")
    options_considered = models.JSONField(help_text="List of options evaluated")
    chosen_option = models.CharField(max_length=500)
    reasoning = models.TextField(help_text="Why this option was chosen")
    
    OUTCOME_CHOICES = [
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    ]
    outcome = models.CharField(
        max_length=20,
        choices=OUTCOME_CHOICES,
        null=True,
        blank=True
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'agent_decisions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['investigation', 'timestamp']),
        ]
    
    def __str__(self):
        return f"Decision: {self.chosen_option[:50]}"