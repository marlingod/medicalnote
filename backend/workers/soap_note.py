import logging

from celery import shared_task
from django.db import transaction

from apps.encounters.models import Encounter, Transcript
from apps.notes.models import ClinicalNote, PromptVersion
from services.llm_service import LLMService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=45,
    time_limit=120,
    name="workers.soap_note.generate_soap_note_task",
)
def generate_soap_note_task(self, encounter_id: str):
    try:
        encounter = Encounter.objects.get(id=encounter_id)
        transcript = Transcript.objects.get(encounter=encounter)
    except (Encounter.DoesNotExist, Transcript.DoesNotExist) as e:
        logger.error(f"Encounter or transcript not found: {encounter_id}")
        return

    try:
        prompt_version = PromptVersion.objects.filter(
            prompt_name="soap_note", is_active=True
        ).first()
        version_str = prompt_version.version if prompt_version else "1.0.0"

        practice = encounter.doctor.practice if encounter.doctor else None
        llm = LLMService(practice=practice)
        result = llm.generate_soap_note(transcript.raw_text, version_str)

        with transaction.atomic():
            ClinicalNote.objects.update_or_create(
                encounter=encounter,
                defaults={
                    "note_type": "soap",
                    "subjective": result["subjective"],
                    "objective": result["objective"],
                    "assessment": result["assessment"],
                    "plan": result["plan"],
                    "icd10_codes": result.get("icd10_codes", []),
                    "cpt_codes": result.get("cpt_codes", []),
                    "ai_generated": True,
                    "doctor_edited": False,
                    "prompt_version": prompt_version,
                },
            )
            encounter.status = Encounter.Status.GENERATING_SUMMARY
            encounter.save(update_fields=["status", "updated_at"])

        from workers.summary import generate_summary_task
        generate_summary_task.delay(encounter_id)

        # Auto-trigger quality scoring
        from workers.quality_checker import quality_checker_task
        quality_checker_task.delay(encounter_id)

        _send_ws_update(encounter_id, "generating_summary")

    except ValueError as exc:
        logger.warning(f"LLM output validation failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="note_generation_failed")
        _send_ws_update(encounter_id, "note_generation_failed")
    except Exception as exc:
        logger.error(f"SOAP note task failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="note_generation_failed")
        _send_ws_update(encounter_id, "note_generation_failed")


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
