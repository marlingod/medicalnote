import logging

from celery import shared_task
from django.db import transaction

from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote
from apps.quality.models import QualityFinding, QualityRule, QualityScore
from services.quality_rules_engine import QualityRulesEngine

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    retry_backoff=True,
    time_limit=60,
    name="workers.quality_checker.quality_checker_task",
)
def quality_checker_task(self, encounter_id: str):
    try:
        encounter = Encounter.objects.get(id=encounter_id)
        note = ClinicalNote.objects.get(encounter=encounter)
    except (Encounter.DoesNotExist, ClinicalNote.DoesNotExist) as e:
        logger.error(f"Encounter or note not found: {encounter_id}")
        return

    try:
        engine = QualityRulesEngine()
        result = engine.evaluate_note(note)

        with transaction.atomic():
            # Delete existing score and findings for re-check
            QualityScore.objects.filter(encounter=encounter).delete()

            score = QualityScore.objects.create(
                encounter=encounter,
                clinical_note=note,
                overall_score=result["overall_score"],
                completeness_score=result["completeness_score"],
                billing_score=result["billing_score"],
                compliance_score=result["compliance_score"],
                suggested_em_level=result["suggested_em_level"],
                suggestions=[
                    f["message"]
                    for f in result["findings"]
                    if not f["passed"]
                ],
            )

            # Create findings linked to QualityRule records
            for finding_data in result["findings"]:
                rule, _ = QualityRule.objects.get_or_create(
                    rule_code=finding_data["rule_code"],
                    defaults={
                        "name": finding_data["rule_code"],
                        "category": finding_data["category"],
                        "severity": finding_data["severity"],
                        "points": finding_data["points"],
                    },
                )
                QualityFinding.objects.create(
                    quality_score=score,
                    rule=rule,
                    passed=finding_data["passed"],
                    message=finding_data["message"],
                )

        _send_ws_update(encounter_id, "quality_checked")
        logger.info(
            f"Quality score for {encounter_id}: "
            f"{result['overall_score']}/100"
        )

    except Exception as exc:
        logger.error(
            f"Quality check failed for {encounter_id}: {exc}"
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)


def _send_ws_update(encounter_id: str, status: str):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"encounter_{encounter_id}",
            {
                "type": "job_status_update",
                "status": status,
                "encounter_id": encounter_id,
            },
        )
    except Exception as e:
        logger.warning(f"WebSocket update failed: {e}")
