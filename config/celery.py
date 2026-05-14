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
    'daily-competitor-monitoring': {
        'task': 'apps.scraping.tasks.run_daily_monitoring',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    'update-analytics-hourly': {
        'task': 'apps.analytics.tasks.update_competitor_analytics',
        'schedule': crontab(minute=0),  # Run every hour
    },
    'daily-linkedin-monitoring': {
        'task': 'apps.social_media.tasks.run_linkedin_monitoring',
        'schedule': crontab(hour=3, minute=0),  # Run daily at 3 AM (1h after website scraping)
    },
    'fetch-competitors-news': {
        'task': 'apps.scraping.tasks.fetch_all_competitors_news',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
