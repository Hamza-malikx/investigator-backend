from django.db import models
import uuid

class Evidence(models.Model):
    """Evidence collected during investigation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.ForeignKey('investigations.Investigation', on_delete=models.CASCADE, related_name='evidence')
    
    EVIDENCE_TYPE_CHOICES = [
        ('document', 'Document'),
        ('web_page', 'Web Page'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('testimony', 'Testimony'),
        ('financial_record', 'Financial Record'),
    ]
    evidence_type = models.CharField(max_length=30, choices=EVIDENCE_TYPE_CHOICES)
    
    title = models.CharField(max_length=300)
    content = models.TextField(help_text="Extracted or summarized content")
    source_url = models.URLField(null=True, blank=True)
    
    CREDIBILITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('unverified', 'Unverified'),
    ]
    source_credibility = models.CharField(max_length=20, choices=CREDIBILITY_CHOICES, default='unverified')
    
    # File storage
    file_path = models.FileField(upload_to='evidence/%Y/%m/%d/', null=True, blank=True)
    file_type = models.CharField(max_length=50, null=True, blank=True)
    
    metadata = models.JSONField(default=dict, help_text="Publication date, author, etc.")
    
    discovered_by_task = models.ForeignKey('investigations.SubTask', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'evidence'
        indexes = [
            models.Index(fields=['investigation', 'evidence_type']),
        ]
    
    def __str__(self):
        return f"{self.evidence_type}: {self.title}"


class EvidenceEntityLink(models.Model):
    """Links between evidence and entities"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evidence = models.ForeignKey(Evidence, on_delete=models.CASCADE, related_name='entity_links')
    entity = models.ForeignKey('entities.Entity', on_delete=models.CASCADE, related_name='evidence_links')
    
    RELEVANCE_CHOICES = [
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('mentioned', 'Mentioned'),
    ]
    relevance = models.CharField(max_length=20, choices=RELEVANCE_CHOICES)
    quote = models.TextField(null=True, blank=True, help_text="Specific quote linking them")
    
    class Meta:
        db_table = 'evidence_entity_links'
        unique_together = [['evidence', 'entity']]


class EvidenceRelationshipLink(models.Model):
    """Links between evidence and relationships"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evidence = models.ForeignKey(Evidence, on_delete=models.CASCADE, related_name='relationship_links')
    relationship = models.ForeignKey('entities.Relationship', on_delete=models.CASCADE, related_name='evidence_links')
    
    supports = models.BooleanField(help_text="True if supports, False if contradicts")
    strength = models.FloatField(default=0.5, help_text="How strongly it supports/contradicts")
    quote = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'evidence_relationship_links'
        unique_together = [['evidence', 'relationship']]