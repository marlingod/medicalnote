from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin
from apps.encounters.models import Encounter, Transcript
from apps.encounters.serializers import (
    EncounterDetailSerializer,
    EncounterSerializer,
    PasteInputSerializer,
    DictationInputSerializer,
    TranscriptSerializer,
)


class EncounterViewSet(viewsets.ModelViewSet):
    serializer_class = EncounterSerializer
    permission_classes = [IsDoctorOrAdmin]

    def get_queryset(self):
        return Encounter.objects.filter(
            doctor__practice=self.request.user.practice
        ).select_related("doctor", "patient")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return EncounterDetailSerializer
        return EncounterSerializer

    @action(detail=True, methods=["post"], url_path="paste")
    def paste_input(self, request, pk=None):
        encounter = self.get_object()
        serializer = PasteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]

        # Create transcript directly from pasted text
        Transcript.objects.update_or_create(
            encounter=encounter,
            defaults={
                "raw_text": text,
                "speaker_segments": [],
                "confidence_score": 1.0,
                "language_detected": "en",
            },
        )

        encounter.status = Encounter.Status.GENERATING_NOTE
        encounter.save(update_fields=["status", "updated_at"])

        # Dispatch SOAP note worker
        from workers.soap_note import generate_soap_note_task

        generate_soap_note_task.delay(str(encounter.id))

        return Response(
            {"status": "processing", "encounter_id": str(encounter.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="dictation")
    def dictation_input(self, request, pk=None):
        encounter = self.get_object()
        serializer = DictationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]

        Transcript.objects.update_or_create(
            encounter=encounter,
            defaults={
                "raw_text": text,
                "speaker_segments": [],
                "confidence_score": 1.0,
                "language_detected": "en",
            },
        )

        encounter.status = Encounter.Status.GENERATING_NOTE
        encounter.save(update_fields=["status", "updated_at"])

        from workers.soap_note import generate_soap_note_task

        generate_soap_note_task.delay(str(encounter.id))

        return Response(
            {"status": "processing", "encounter_id": str(encounter.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="recording")
    def upload_recording(self, request, pk=None):
        encounter = self.get_object()
        audio_file = request.FILES.get("audio")
        if not audio_file:
            return Response(
                {"error": "Audio file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from services.storage_service import StorageService
        from apps.encounters.models import Recording

        storage = StorageService()
        storage_url = storage.upload_audio(audio_file, encounter.id)

        Recording.objects.update_or_create(
            encounter=encounter,
            defaults={
                "storage_url": storage_url,
                "duration_seconds": 0,  # Updated after transcription
                "file_size_bytes": audio_file.size,
                "format": audio_file.name.rsplit(".", 1)[-1] if "." in audio_file.name else "wav",
                "transcription_status": "pending",
            },
        )

        encounter.status = Encounter.Status.TRANSCRIBING
        encounter.save(update_fields=["status", "updated_at"])

        from workers.transcription import transcription_task

        transcription_task.delay(str(encounter.id))

        return Response(
            {"status": "transcribing", "encounter_id": str(encounter.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="scan")
    def upload_scan(self, request, pk=None):
        encounter = self.get_object()
        scan_file = request.FILES.get("image")
        if not scan_file:
            return Response(
                {"error": "Image file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from services.storage_service import StorageService

        storage = StorageService()
        storage_url = storage.upload_scan(scan_file, encounter.id)

        encounter.status = Encounter.Status.TRANSCRIBING
        encounter.save(update_fields=["status", "updated_at"])

        from workers.ocr import ocr_task

        ocr_task.delay(str(encounter.id), storage_url)

        return Response(
            {"status": "processing_scan", "encounter_id": str(encounter.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"], url_path="transcript")
    def get_transcript(self, request, pk=None):
        encounter = self.get_object()
        try:
            transcript = encounter.transcript
        except Transcript.DoesNotExist:
            return Response(
                {"error": "No transcript available."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = TranscriptSerializer(transcript)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="voice-transcript")
    def voice_transcript(self, request, pk=None):
        """Accept pre-transcribed text from on-device Whisper (mobile offline mode)."""
        encounter = self.get_object()
        text = request.data.get("text", "").strip()
        confidence = request.data.get("confidence", 0.0)
        language = request.data.get("language", "en")

        if len(text) < 10:
            return Response(
                {"error": "Transcript text must be at least 10 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Transcript.objects.update_or_create(
            encounter=encounter,
            defaults={
                "raw_text": text,
                "speaker_segments": [],
                "medical_terms_detected": [],
                "confidence_score": float(confidence),
                "language_detected": language,
            },
        )

        encounter.status = Encounter.Status.GENERATING_NOTE
        encounter.save(update_fields=["status", "updated_at"])

        from workers.soap_note import generate_soap_note_task

        generate_soap_note_task.delay(str(encounter.id))

        return Response(
            {"status": "processing", "encounter_id": str(encounter.id)},
            status=status.HTTP_202_ACCEPTED,
        )
