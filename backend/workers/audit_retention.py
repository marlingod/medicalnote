import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="audit.archive_old_logs")
def archive_old_audit_logs():
    """Archive audit logs older than 1 year. HIPAA 164.530(j) requires 6-year retention."""
    from apps.audit.models import AuditLog

    cutoff = timezone.now() - timedelta(days=365)
    old_logs = AuditLog.objects.filter(created_at__lt=cutoff, archived=False)
    count = old_logs.count()

    if count == 0:
        logger.info("No audit logs to archive.")
        return {"archived": 0}

    # Mark as archived (actual S3 export would be done in production)
    old_logs.update(archived=True)

    logger.info(f"Archived {count} audit logs older than {cutoff.isoformat()}")
    return {"archived": count, "cutoff": cutoff.isoformat()}
