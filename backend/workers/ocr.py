import logging

from celery import shared_task
from django.db import transaction

from apps.encounters.models import Encounter, Transcript
from services.ocr_service import OCRService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=45,
    time_limit=120,
    name="workers.ocr.ocr_task",
)
def ocr_task(self, encounter_id: str, s3_uri: str):
    try:
        encounter = Encounter.objects.get(id=encounter_id)
    except Encounter.DoesNotExist:
        logger.error(f"Encounter not found: {encounter_id}")
        return

    try:
        ocr_service = OCRService()
        extracted_text = ocr_service.extract_text_from_s3(s3_uri)

        if not extracted_text.strip():
            raise ValueError("OCR extracted no text from image.")

        with transaction.atomic():
            Transcript.objects.update_or_create(
                encounter=encounter,
                defaults={
                    "raw_text": extracted_text,
                    "speaker_segments": [],
                    "confidence_score": 0.85,
                    "language_detected": "en",
                },
            )
            encounter.status = Encounter.Status.GENERATING_NOTE
            encounter.save(update_fields=["status", "updated_at"])

        from workers.soap_note import generate_soap_note_task
        generate_soap_note_task.delay(encounter_id)

        _send_ws_update(encounter_id, "generating_note")

    except Exception as exc:
        logger.error(f"OCR task failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="transcription_failed")
        _send_ws_update(encounter_id, "transcription_failed")


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
