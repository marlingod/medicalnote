from datetime import date
from unittest.mock import MagicMock, patch
from django.test import TestCase
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.patients.models import Patient


class OCRTaskTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="scan", status="transcribing",
        )

    @patch("workers.ocr.OCRService")
    @patch("workers.soap_note.generate_soap_note_task")
    def test_ocr_success(self, mock_soap_task, mock_ocr_cls):
        mock_ocr = MagicMock()
        mock_ocr_cls.return_value = mock_ocr
        mock_ocr.extract_text_from_s3.return_value = "Chief Complaint: Headache\nBP: 120/80"

        from workers.ocr import ocr_task
        ocr_task(str(self.encounter.id), "s3://bucket/scan.jpg")

        self.encounter.refresh_from_db()
        assert self.encounter.status == "generating_note"
        assert hasattr(self.encounter, "transcript")
