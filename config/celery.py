"""
Celery configuration for async tasks and scheduled jobs.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('competitor_monitoring')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Scheduled tasks
app.conf.beat_schedule = {
    'scrape-competitors-daily': {
        'task': 'apps.scraping.tasks.scrape_all_competitors',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    'update-analytics-hourly': {
        'task': 'apps.analytics.tasks.update_competitor_analytics',
        'schedule': crontab(minute=0),  # Run every hour
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
