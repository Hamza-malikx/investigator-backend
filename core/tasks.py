import logging
from typing import Dict, List
from celery import shared_task
from django.utils import timezone
from django.db import transaction

from investigations.models import Investigation, InvestigationPlan, SubTask
from entities.models import Entity, Relationship
from evidence.models import Evidence, EvidenceEntityLink
from core.gemini_client import gemini_client
from core.websocket_utils import (
    broadcast_status_update,
    broadcast_entity_discovered,
    broadcast_relationship_discovered,
    broadcast_evidence_discovered,
    broadcast_thought_update,
    broadcast_progress_update,
    broadcast_error
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def run_investigation(self, investigation_id: str):
    """
    Main orchestration task for running an autonomous investigation.
    
    This is the entry point for the entire investigation process.
    """
    logger.info(f"Starting investigation {investigation_id}")
    
    try:
        investigation = Investigation.objects.get(id=investigation_id)
        
        # Update status to running
        investigation.status = 'running'
        investigation.current_phase = 'planning'
        investigation.started_at = timezone.now()
        investigation.save()
        
        broadcast_status_update(
            investigation_id,
            'running',
            current_phase='planning',
            progress=5
        )
        
        # Phase 1: Generate investigation plan
        plan = generate_investigation_plan(investigation)
        
        if not plan:
            raise Exception("Failed to generate investigation plan")
        
        # Update progress
        investigation.progress_percentage = 10
        investigation.current_phase = 'researching'
        investigation.save()
        
        broadcast_progress_update(investigation_id, {
            'progress_percentage': 10,
            'current_phase': 'researching',
            'message': 'Investigation plan created, starting research...'
        })
        
        # Phase 2: Execute subtasks
        subtasks = investigation.subtasks.filter(status='pending').order_by('order')
        total_tasks = subtasks.count()
        
        for idx, subtask in enumerate(subtasks):
            if investigation.status != 'running':
                logger.info(f"Investigation {investigation_id} paused or cancelled")
                break
            
            # Execute subtask
            execute_subtask.delay(subtask.id, investigation_id)
            
            # Update progress
            progress = 10 + int((idx + 1) / total_tasks * 70)
            investigation.progress_percentage = progress
            investigation.save()
            
            broadcast_progress_update(investigation_id, {
                'progress_percentage': progress,
                'current_phase': 'researching',
                'completed_tasks': idx + 1,
                'total_tasks': total_tasks
            })
        
        # Phase 3: Analysis and completion
        investigation.current_phase = 'analyzing'
        investigation.progress_percentage = 85
        investigation.save()
        
        broadcast_status_update(
            investigation_id,
            'running',
            current_phase='analyzing',
            progress=85
        )
        
        # Phase 4: Mark as completed
        investigation.status = 'completed'
        investigation.current_phase = 'completed'
        investigation.progress_percentage = 100
        investigation.completed_at = timezone.now()
        investigation.save()
        
        broadcast_status_update(
            investigation_id,
            'completed',
            current_phase='completed',
            progress=100
        )
        
        logger.info(f"Investigation {investigation_id} completed successfully")
        
    except Investigation.DoesNotExist:
        logger.error(f"Investigation {investigation_id} not found")
        
    except Exception as e:
        logger.error(f"Error in investigation {investigation_id}: {e}")
        
        try:
            investigation = Investigation.objects.get(id=investigation_id)
            investigation.status = 'failed'
            investigation.save()
            
            broadcast_error(
                investigation_id,
                f"Investigation failed: {str(e)}",
                error_type='investigation_failed'
            )
        except:
            pass
        
        raise


def generate_investigation_plan(investigation: Investigation) -> bool:
    """Generate investigation plan using Gemini AI"""
    try:
        # Get or create plan
        plan, created = InvestigationPlan.objects.get_or_create(
            investigation=investigation
        )
        
        # Use Gemini to generate plan
        ai_plan = gemini_client.plan_investigation(
            query=investigation.initial_query,
            focus_areas=plan.priority_areas,
            depth_level='moderate'
        )
        
        # Update plan
        plan.hypothesis = ai_plan.get('hypothesis', '')
        plan.research_strategy = ai_plan.get('strategy', [])
        plan.save()
        
        # Create subtasks
        subtasks_data = ai_plan.get('subtasks', [])
        for task_data in subtasks_data:
            SubTask.objects.create(
                investigation=investigation,
                task_type=task_data.get('type', 'web_search'),
                description=task_data.get('description', ''),
                order=task_data.get('order', 0),
                status='pending'
            )
        
        # Estimate completion
        duration_minutes = ai_plan.get('estimated_duration_minutes', 60)
        investigation.estimated_completion = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        investigation.save()
        
        logger.info(f"Generated plan with {len(subtasks_data)} subtasks for investigation {investigation.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating investigation plan: {e}")
        return False


@shared_task(bind=True, max_retries=3)
def execute_subtask(self, subtask_id: str, investigation_id: str):
    """
    Execute a single research subtask.
    """
    logger.info(f"Executing subtask {subtask_id}")
    
    try:
        subtask = SubTask.objects.get(id=subtask_id)
        investigation = Investigation.objects.get(id=investigation_id)
        
        # Update subtask status
        subtask.status = 'in_progress'
        subtask.started_at = timezone.now()
        subtask.save()
        
        # Build context
        context = build_investigation_context(investigation)
        
        # Execute with Gemini
        result = gemini_client.execute_research_step(
            task_description=subtask.description,
            context=context
        )
        
        # Process results
        process_research_results(investigation, result, subtask)
        
        # Generate thought for transparency
        thought = gemini_client.generate_thought(
            current_state={'hypothesis': investigation.plan.hypothesis},
            new_information=f"Completed: {subtask.description}"
        )
        
        broadcast_thought_update(investigation_id, {
            'id': str(subtask.id),
            'type': thought.get('thought_type', 'observation'),
            'content': thought.get('content', ''),
            'confidence': thought.get('confidence_after', 0.5),
            'timestamp': str(timezone.now())
        })
        
        # Update subtask
        subtask.status = 'completed'
        subtask.completed_at = timezone.now()
        subtask.result = result
        subtask.confidence = result.get('confidence', 0.0)
        subtask.save()
        
        # Track API usage
        investigation.total_api_calls += 1
        investigation.save()
        
        logger.info(f"Subtask {subtask_id} completed successfully")
        
    except SubTask.DoesNotExist:
        logger.error(f"Subtask {subtask_id} not found")
        
    except Exception as e:
        logger.error(f"Error executing subtask {subtask_id}: {e}")
        
        try:
            subtask = SubTask.objects.get(id=subtask_id)
            subtask.status = 'failed'
            subtask.save()
        except:
            pass
        
        # Retry
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)


def build_investigation_context(investigation: Investigation) -> Dict:
    """Build context for Gemini API calls"""
    entities = investigation.entities.all()
    relationships = investigation.relationships.all()
    
    return {
        'query': investigation.initial_query,
        'hypothesis': investigation.plan.hypothesis if hasattr(investigation, 'plan') else '',
        'entities': [
            {
                'name': e.name,
                'type': e.entity_type,
                'confidence': e.confidence
            }
            for e in entities
        ],
        'relationships': [
            {
                'source': r.source_entity.name,
                'target': r.target_entity.name,
                'type': r.relationship_type
            }
            for r in relationships
        ],
        'current_phase': investigation.current_phase
    }


@transaction.atomic
def process_research_results(investigation: Investigation, result: Dict, subtask: SubTask):
    """Process and save research results to database"""
    
    # Process entities
    entities_data = result.get('entities', [])
    for entity_data in entities_data:
        entity, created = Entity.objects.get_or_create(
            investigation=investigation,
            name=entity_data.get('name', 'Unknown'),
            entity_type=entity_data.get('type', 'unknown'),
            defaults={
                'description': entity_data.get('description', ''),
                'confidence': entity_data.get('confidence', 0.5),
                'discovered_by_task': subtask,
                'source_count': 1
            }
        )
        
        if created:
            # Broadcast new entity (signal will also broadcast)
            logger.info(f"Discovered new entity: {entity.name}")
    
    # Process relationships
    relationships_data = result.get('relationships', [])
    for rel_data in relationships_data:
        # Find or create entities
        source_entity = Entity.objects.filter(
            investigation=investigation,
            name=rel_data.get('source')
        ).first()
        
        target_entity = Entity.objects.filter(
            investigation=investigation,
            name=rel_data.get('target')
        ).first()
        
        if source_entity and target_entity:
            relationship, created = Relationship.objects.get_or_create(
                investigation=investigation,
                source_entity=source_entity,
                target_entity=target_entity,
                relationship_type=rel_data.get('type', 'connected_to'),
                defaults={
                    'description': rel_data.get('description', ''),
                    'confidence': rel_data.get('confidence', 0.5),
                    'discovered_by_task': subtask,
                    'strength': rel_data.get('confidence', 0.5)
                }
            )
            
            if created:
                logger.info(f"Discovered new relationship: {source_entity.name} -> {target_entity.name}")
    
    # Process evidence
    evidence_data = result.get('evidence', [])
    for ev_data in evidence_data:
        evidence = Evidence.objects.create(
            investigation=investigation,
            evidence_type='web_page',
            title=ev_data.get('title', 'Evidence'),
            content=ev_data.get('content', ''),
            source_url=ev_data.get('source', ''),
            source_credibility=ev_data.get('credibility', 'medium'),
            discovered_by_task=subtask
        )
        
        logger.info(f"Collected new evidence: {evidence.title}")


@shared_task
def analyze_document(evidence_id: str):
    """
    Analyze uploaded document for entities and relationships.
    """
    logger.info(f"Analyzing document {evidence_id}")
    
    try:
        evidence = Evidence.objects.get(id=evidence_id)
        investigation = evidence.investigation
        
        # Extract entities from content
        entities_data = gemini_client.extract_entities(
            text=evidence.content,
            context={'query': investigation.initial_query}
        )
        
        # Create entities and link to evidence
        for entity_data in entities_data:
            entity, created = Entity.objects.get_or_create(
                investigation=investigation,
                name=entity_data.get('name'),
                entity_type=entity_data.get('type', 'unknown'),
                defaults={
                    'description': entity_data.get('description', ''),
                    'confidence': entity_data.get('confidence', 0.5),
                    'source_count': 1
                }
            )
            
            # Link entity to evidence
            EvidenceEntityLink.objects.get_or_create(
                evidence=evidence,
                entity=entity,
                defaults={'relevance': 'primary'}
            )
        
        logger.info(f"Document analysis complete for {evidence_id}")
        
    except Evidence.DoesNotExist:
        logger.error(f"Evidence {evidence_id} not found")
    except Exception as e:
        logger.error(f"Error analyzing document {evidence_id}: {e}")


@shared_task
def generate_report(investigation_id: str, report_type: str = 'executive_summary'):
    """
    Generate investigation report using Gemini.
    """
    logger.info(f"Generating {report_type} report for investigation {investigation_id}")
    
    try:
        from reports.models import Report
        
        investigation = Investigation.objects.get(id=investigation_id)
        
        # Gather all investigation data
        investigation_data = {
            'title': investigation.title,
            'query': investigation.initial_query,
            'entities': list(investigation.entities.values(
                'name', 'entity_type', 'description', 'confidence'
            )),
            'relationships': list(investigation.relationships.values(
                'source_entity__name', 'target_entity__name',
                'relationship_type', 'description', 'confidence'
            )),
            'evidence': list(investigation.evidence.values(
                'title', 'source_url', 'source_credibility'
            ))
        }
        
        # Generate report content
        report_content = gemini_client.generate_report(
            investigation_data=investigation_data,
            report_type=report_type
        )
        
        # Save report
        report = Report.objects.create(
            investigation=investigation,
            report_type=report_type,
            title=f"{investigation.title} - {report_type.replace('_', ' ').title()}",
            content=report_content,
            format='markdown',
            version=1
        )
        
        logger.info(f"Report {report.id} generated successfully")
        return str(report.id)
        
    except Investigation.DoesNotExist:
        logger.error(f"Investigation {investigation_id} not found")
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise


@shared_task
def cleanup_completed_investigations():
    """Cleanup task: Archive old completed investigations"""
    logger.info("Running cleanup for completed investigations")
    
    try:
        # Find investigations completed more than 30 days ago
        cutoff_date = timezone.now() - timezone.timedelta(days=30)
        old_investigations = Investigation.objects.filter(
            status='completed',
            completed_at__lt=cutoff_date
        )
        
        count = old_investigations.count()
        logger.info(f"Found {count} investigations to archive")
        
        # Here you could move to archive storage, compress, etc.
        # For now, just log
        
        return count
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")


@shared_task
def check_stuck_investigations():
    """Check for investigations that have been running too long"""
    logger.info("Checking for stuck investigations")
    
    try:
        # Find investigations running for more than 24 hours
        cutoff_time = timezone.now() - timezone.timedelta(hours=24)
        stuck_investigations = Investigation.objects.filter(
            status='running',
            started_at__lt=cutoff_time
        )
        
        for investigation in stuck_investigations:
            logger.warning(f"Investigation {investigation.id} appears stuck, marking as failed")
            
            investigation.status = 'failed'
            investigation.save()
            
            broadcast_error(
                investigation.id,
                "Investigation timed out after 24 hours",
                error_type='timeout'
            )
        
        return stuck_investigations.count()
        
    except Exception as e:
        logger.error(f"Error checking stuck investigations: {e}")