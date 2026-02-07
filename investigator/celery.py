import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investigator.settings')

# Create Celery app
app = Celery('investigator')

# Load config from Django settings with 'CELERY_' prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Optional: Configure periodic tasks with Celery Beat
app.conf.beat_schedule = {
    # Cleanup completed investigations daily at 3 AM
    'cleanup-completed-investigations': {
        'task': 'core.tasks.cleanup_completed_investigations',
        'schedule': crontab(hour=3, minute=0),
    },
    
    # Check for stuck investigations every 15 minutes
    'check-stuck-investigations': {
        'task': 'core.tasks.check_stuck_investigations',
        'schedule': crontab(minute='*/15'),
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery setup"""
    print(f'Request: {self.request!r}')