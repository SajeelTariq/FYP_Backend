import logging
from datetime import datetime
from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User

from .models import Report
from .agents.report_agent import ReportAgent

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def generate_report_task(self, report_id: int):
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        logger.error(f"Report {report_id} not found")
        return

    report.status = 'generating'
    report.save(update_fields=['status'])

    try:
        agent = ReportAgent()
        competitor_ids = list(report.competitors.values_list('id', flat=True)) or None

        content = agent.execute(
            user=report.user,
            report_type=report.report_type,
            period_start=report.period_start,
            period_end=report.period_end,
            competitor_ids=competitor_ids,
        )

        if 'error' in content:
            raise Exception(content['error'])

        report.content = content
        report.status = 'completed'
        report.completed_at = timezone.now()
        report.save(update_fields=['content', 'status', 'completed_at'])

        logger.info(f"Report {report_id} completed successfully")

    except Exception as exc:
        logger.exception(f"Report {report_id} generation failed")
        report.status = 'failed'
        report.error_message = str(exc)
        report.save(update_fields=['status', 'error_message'])
        raise self.retry(exc=exc, countdown=60)
