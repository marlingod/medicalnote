import logging

from celery import shared_task
from django.db import transaction

from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.summaries.models import PatientSummary
from services.llm_service import LLMService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=45,
    time_limit=120,
    name="workers.summary.generate_summary_task",
)
def generate_summary_task(self, encounter_id: str):
    try:
        encounter = Encounter.objects.get(id=encounter_id)
        note = ClinicalNote.objects.get(encounter=encounter)
    except (Encounter.DoesNotExist, ClinicalNote.DoesNotExist):
        logger.error(f"Encounter or note not found: {encounter_id}")
        return

    try:
        prompt_version = PromptVersion.objects.filter(
            prompt_name="patient_summary", is_active=True
        ).first()

        patient = encounter.patient
        reading_level = "grade_8"
        language = patient.language_preference if patient else "en"

        practice = encounter.doctor.practice if encounter.doctor else None
        llm = LLMService(practice=practice)
        result = llm.generate_patient_summary(
            subjective=note.subjective,
            objective=note.objective,
            assessment=note.assessment,
            plan=note.plan,
            reading_level=reading_level,
            language=language,
        )

        with transaction.atomic():
            PatientSummary.objects.update_or_create(
                encounter=encounter,
                defaults={
                    "clinical_note": note,
                    "summary_en": result["summary_en"],
                    "summary_es": result.get("summary_es", ""),
                    "reading_level": reading_level,
                    "medical_terms_explained": result.get("medical_terms_explained", []),
                    "delivery_status": "pending",
                    "prompt_version": prompt_version,
                },
            )
            encounter.status = Encounter.Status.READY_FOR_REVIEW
            encounter.save(update_fields=["status", "updated_at"])

        _send_ws_update(encounter_id, "ready_for_review")

    except ValueError as exc:
        logger.warning(f"Summary LLM output invalid for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="summary_generation_failed")
        _send_ws_update(encounter_id, "summary_generation_failed")
    except Exception as exc:
        logger.error(f"Summary task failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="summary_generation_failed")
        _send_ws_update(encounter_id, "summary_generation_failed")


def _send_ws_update(encounter_id: str, status: str):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"encounter_{encounter_id}",
            {"type": "job_status_update", "status": status, "encounter_id": encounter_id},
        )
    except Exception as e:
        logger.warning(f"WebSocket update failed: {e}")
