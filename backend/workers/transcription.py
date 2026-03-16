import json
import logging
import time

import requests
from celery import shared_task
from django.db import transaction

from apps.encounters.models import Encounter, Recording, Transcript
from services.stt_service import STTService
from services.storage_service import StorageService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    retry_backoff_max=90,
    time_limit=300,
    name="workers.transcription.transcription_task",
)
def transcription_task(self, encounter_id: str):
    try:
        encounter = Encounter.objects.select_related("recording").get(id=encounter_id)
        recording = encounter.recording
    except (Encounter.DoesNotExist, Recording.DoesNotExist) as e:
        logger.error(f"Encounter or recording not found: {encounter_id}")
        return

    try:
        stt = STTService()
        job_result = stt.start_transcription(recording.storage_url, encounter_id)
        job_name = job_result["job_name"]

        # Poll for completion (in production, use SNS callback)
        max_polls = 60
        for _ in range(max_polls):
            result = stt.get_transcription_result(job_name)
            if result["status"] == "COMPLETED":
                break
            if result["status"] == "FAILED":
                raise Exception(f"Transcription failed: {result.get('failure_reason')}")
            time.sleep(5)
        else:
            raise Exception("Transcription timed out")

        # Fetch and parse transcript
        storage = StorageService()
        transcript_url = storage.get_presigned_url(result["transcript_uri"])
        transcript_response = requests.get(transcript_url, timeout=30)
        transcript_data = json.loads(transcript_response.text)

        raw_text = ""
        speaker_segments = []
        if "results" in transcript_data:
            transcripts = transcript_data["results"].get("transcripts", [])
            raw_text = " ".join(t.get("transcript", "") for t in transcripts)
            segments_data = transcript_data["results"].get("speaker_labels", {}).get("segments", [])
            for seg in segments_data:
                speaker_segments.append({
                    "speaker": seg.get("speaker_label", "unknown"),
                    "start": float(seg.get("start_time", 0)),
                    "end": float(seg.get("end_time", 0)),
                    "text": " ".join(
                        item.get("alternatives", [{}])[0].get("content", "")
                        for item in seg.get("items", [])
                    ),
                })

        with transaction.atomic():
            Transcript.objects.update_or_create(
                encounter=encounter,
                defaults={
                    "raw_text": raw_text,
                    "speaker_segments": speaker_segments,
                    "confidence_score": 0.9,
                    "language_detected": "en",
                },
            )
            recording.transcription_status = "completed"
            recording.save(update_fields=["transcription_status"])
            encounter.status = Encounter.Status.GENERATING_NOTE
            encounter.save(update_fields=["status", "updated_at"])

        # Chain to SOAP note generation
        from workers.soap_note import generate_soap_note_task
        generate_soap_note_task.delay(encounter_id)

        _send_ws_update(encounter_id, "generating_note")

    except Exception as exc:
        logger.error(f"Transcription task failed for {encounter_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        Encounter.objects.filter(id=encounter_id).update(status="transcription_failed")
        Recording.objects.filter(encounter_id=encounter_id).update(transcription_status="failed")
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
        logger.warning(f"WebSocket update failed for {encounter_id}: {e}")
