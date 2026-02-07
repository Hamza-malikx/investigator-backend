from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from entities.models import Entity, Relationship
from evidence.models import Evidence
from investigations.models import Investigation


@receiver(post_save, sender=Entity)
def entity_created_signal(sender, instance, created, **kwargs):
    """Broadcast when a new entity is created"""
    if created:
        from core.websocket_utils import broadcast_entity_discovered
        broadcast_entity_discovered(instance.investigation_id, instance)


@receiver(post_save, sender=Relationship)
def relationship_created_signal(sender, instance, created, **kwargs):
    """Broadcast when a new relationship is created"""
    if created:
        from core.websocket_utils import broadcast_relationship_discovered
        broadcast_relationship_discovered(instance.investigation_id, instance)


@receiver(post_save, sender=Evidence)
def evidence_created_signal(sender, instance, created, **kwargs):
    """Broadcast when new evidence is created"""
    if created:
        from core.websocket_utils import broadcast_evidence_discovered
        broadcast_evidence_discovered(instance.investigation_id, instance)


@receiver(pre_save, sender=Investigation)
def investigation_status_changed_signal(sender, instance, **kwargs):
    """Broadcast when investigation status changes"""
    if instance.pk:  # Only for updates, not creation
        try:
            old_instance = Investigation.objects.get(pk=instance.pk)
            
            # Check if status or phase changed
            if (old_instance.status != instance.status or 
                old_instance.current_phase != instance.current_phase or
                old_instance.progress_percentage != instance.progress_percentage):
                
                from core.websocket_utils import broadcast_status_update
                broadcast_status_update(
                    instance.id,
                    instance.status,
                    current_phase=instance.current_phase,
                    progress=instance.progress_percentage
                )
        except Investigation.DoesNotExist:
            pass