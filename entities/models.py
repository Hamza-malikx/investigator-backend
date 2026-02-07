from django.db import models
import uuid

class Entity(models.Model):
    """Entities discovered during investigation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.ForeignKey('investigations.Investigation', on_delete=models.CASCADE, related_name='entities')
    
    ENTITY_TYPE_CHOICES = [
        ('person', 'Person'),
        ('company', 'Company'),
        ('location', 'Location'),
        ('event', 'Event'),
        ('document', 'Document'),
        ('financial_instrument', 'Financial Instrument'),
    ]
    entity_type = models.CharField(max_length=30, choices=ENTITY_TYPE_CHOICES)
    
    name = models.CharField(max_length=200)
    aliases = models.JSONField(default=list, help_text="Alternative names")
    description = models.TextField(blank=True)
    
    # Confidence & validation
    confidence = models.FloatField(default=0.0)
    source_count = models.IntegerField(default=0, help_text="Number of sources mentioning this entity")
    
    # Type-specific data
    metadata = models.JSONField(default=dict, help_text="Type-specific information")
    
    # Graph visualization
    position_x = models.FloatField(null=True, blank=True)
    position_y = models.FloatField(null=True, blank=True)
    
    discovered_by_task = models.ForeignKey('investigations.SubTask', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'entities'
        unique_together = [['investigation', 'name', 'entity_type']]
        indexes = [
            models.Index(fields=['investigation', 'entity_type']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.entity_type}: {self.name}"


class Relationship(models.Model):
    """Relationships between entities"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.ForeignKey('investigations.Investigation', on_delete=models.CASCADE, related_name='relationships')
    
    source_entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='outgoing_relationships')
    target_entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='incoming_relationships')
    
    RELATIONSHIP_TYPE_CHOICES = [
        ('owns', 'Owns'),
        ('works_for', 'Works For'),
        ('connected_to', 'Connected To'),
        ('transacted_with', 'Transacted With'),
        ('located_in', 'Located In'),
        ('parent_of', 'Parent Of'),
    ]
    relationship_type = models.CharField(max_length=30, choices=RELATIONSHIP_TYPE_CHOICES)
    description = models.TextField(blank=True)
    
    confidence = models.FloatField(default=0.0)
    strength = models.FloatField(default=0.5, help_text="Relationship strength for visualization")
    
    # Time validity
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    discovered_by_task = models.ForeignKey('investigations.SubTask', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'relationships'
        indexes = [
            models.Index(fields=['investigation', 'relationship_type']),
            models.Index(fields=['source_entity', 'target_entity']),
        ]
    
    def __str__(self):
        return f"{self.source_entity.name} {self.relationship_type} {self.target_entity.name}"