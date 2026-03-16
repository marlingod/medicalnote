import uuid
from datetime import date

from django.test import TestCase

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter, Recording, Transcript
from apps.patients.models import Patient


class EncounterModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
        )

    def test_create_encounter(self):
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="recording",
            status="uploading",
            consent_recording=True,
            consent_method="verbal",
            consent_jurisdiction_state="CA",
        )
        assert encounter.id is not None
        assert isinstance(encounter.id, uuid.UUID)
        assert encounter.status == "uploading"

    def test_encounter_status_choices(self):
        encounter = Encounter(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="recording",
            status="invalid_status",
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            encounter.full_clean()

    def test_encounter_input_method_choices(self):
        for method in ["recording", "paste", "dictation", "scan"]:
            encounter = Encounter.objects.create(
                doctor=self.doctor,
                patient=self.patient,
                encounter_date=date.today(),
                input_method=method,
                status="uploading",
            )
            assert encounter.input_method == method

    def test_encounter_str(self):
        encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date(2026, 3, 15),
            input_method="recording",
            status="uploading",
        )
        result = str(encounter)
        assert "2026-03-15" in result or str(encounter.id) in result


class RecordingModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="recording",
            status="uploading",
        )

    def test_create_recording(self):
        recording = Recording.objects.create(
            encounter=self.encounter,
            storage_url="s3://bucket/audio/test.wav",
            duration_seconds=1800,
            file_size_bytes=54000000,
            format="wav",
            transcription_status="pending",
        )
        assert recording.id is not None
        assert recording.duration_seconds == 1800

    def test_recording_format_choices(self):
        for fmt in ["wav", "mp3", "webm"]:
            recording = Recording(
                encounter=self.encounter,
                storage_url=f"s3://bucket/{fmt}",
                format=fmt,
                transcription_status="pending",
            )
            recording.full_clean()  # Should not raise


class TranscriptModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="recording",
            status="transcribing",
        )

    def test_create_transcript(self):
        transcript = Transcript.objects.create(
            encounter=self.encounter,
            raw_text="Doctor: How are you? Patient: I have a headache.",
            speaker_segments=[
                {"speaker": "doctor", "start": 0.0, "end": 2.5, "text": "How are you?"},
                {"speaker": "patient", "start": 2.5, "end": 5.0, "text": "I have a headache."},
            ],
            medical_terms_detected=["headache"],
            confidence_score=0.95,
            language_detected="en",
        )
        assert transcript.id is not None
        assert len(transcript.speaker_segments) == 2
        assert transcript.confidence_score == 0.95
