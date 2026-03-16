from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import DeviceToken, Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


class SummaryAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D", date_of_birth="1990-01-01"
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="paste", status="approved",
        )
        self.pv = PromptVersion.objects.create(
            prompt_name="patient_summary", version="1.0.0", template_text="t", is_active=True
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter, note_type="soap",
            subjective="S", objective="O", assessment="A", plan="P",
            prompt_version=self.pv,
        )
        self.summary = PatientSummary.objects.create(
            encounter=self.encounter, clinical_note=self.note,
            summary_en="Your visit summary.", reading_level="grade_8",
            disclaimer_text="Disclaimer.", delivery_status="pending",
            prompt_version=self.pv,
        )
        self.client.force_authenticate(user=self.doctor)

    def test_get_summary_for_encounter(self):
        response = self.client.get(f"/api/v1/encounters/{self.encounter.id}/summary/")
        assert response.status_code == status.HTTP_200_OK
        assert "Your visit summary" in response.data["summary_en"]

    def test_send_summary(self):
        response = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/summary/send/",
            {"delivery_method": "app"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        self.summary.refresh_from_db()
        assert self.summary.delivery_status == "sent"

    def test_get_summary_not_found(self):
        encounter2 = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient,
            encounter_date=date.today(), input_method="paste", status="uploading",
        )
        response = self.client.get(f"/api/v1/encounters/{encounter2.id}/summary/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class PatientFacingSummaryAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient_record = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D",
            date_of_birth="1990-01-01", phone="+15551234567",
        )
        self.patient_user = User.objects.create_user(
            email="+15551234567@patient.medicalnote.local",
            role="patient", phone="+15551234567",
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient_record,
            encounter_date=date.today(), input_method="paste", status="delivered",
        )
        self.pv = PromptVersion.objects.create(
            prompt_name="patient_summary", version="1.0.0", template_text="t", is_active=True
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter, note_type="soap",
            subjective="S", objective="O", assessment="A", plan="P",
            prompt_version=self.pv,
        )
        self.summary = PatientSummary.objects.create(
            encounter=self.encounter, clinical_note=self.note,
            summary_en="Summary.", reading_level="grade_8",
            disclaimer_text="Disclaimer.", delivery_status="sent",
            prompt_version=self.pv,
        )
        self.client.force_authenticate(user=self.patient_user)

    def test_patient_list_own_summaries(self):
        response = self.client.get("/api/v1/patient/summaries/")
        assert response.status_code == status.HTTP_200_OK

    def test_patient_mark_summary_read(self):
        response = self.client.patch(
            f"/api/v1/patient/summaries/{self.summary.id}/read/"
        )
        assert response.status_code == status.HTTP_200_OK
        self.summary.refresh_from_db()
        assert self.summary.delivery_status == "viewed"
        assert self.summary.viewed_at is not None


class SendSummaryPushNotificationTest(TestCase):
    """Tests that send_summary triggers push notifications to patient devices."""

    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.patient_record = Patient.objects.create(
            practice=self.practice, first_name="J", last_name="D",
            date_of_birth="1990-01-01", phone="+15551234567",
        )
        self.patient_user = User.objects.create_user(
            email="+15551234567@patient.medicalnote.local",
            role="patient", phone="+15551234567",
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor, patient=self.patient_record,
            encounter_date=date.today(), input_method="paste", status="approved",
        )
        self.pv = PromptVersion.objects.create(
            prompt_name="patient_summary", version="1.0.0", template_text="t", is_active=True
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter, note_type="soap",
            subjective="S", objective="O", assessment="A", plan="P",
            prompt_version=self.pv,
        )
        self.summary = PatientSummary.objects.create(
            encounter=self.encounter, clinical_note=self.note,
            summary_en="Your visit summary.", reading_level="grade_8",
            disclaimer_text="Disclaimer.", delivery_status="pending",
            prompt_version=self.pv,
        )
        self.device_token = DeviceToken.objects.create(
            user=self.patient_user, token="fcm-device-token-xyz", platform="ios"
        )
        self.client.force_authenticate(user=self.doctor)

    @patch("apps.summaries.views.NotificationService")
    def test_send_summary_triggers_push_notification(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        response = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/summary/send/",
            {"delivery_method": "app"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        mock_service.send_push_notification.assert_called_once_with(
            device_token="fcm-device-token-xyz",
            title="New Visit Summary",
            body="Your doctor has sent you a new visit summary.",
            data={"summary_id": str(self.summary.id)},
        )

    @patch("apps.summaries.views.NotificationService")
    def test_send_summary_no_push_when_no_device_token(self, mock_service_cls):
        self.device_token.delete()
        mock_service = mock_service_cls.return_value
        response = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/summary/send/",
            {"delivery_method": "app"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        mock_service.send_push_notification.assert_not_called()

    @patch("apps.summaries.views.NotificationService")
    def test_send_summary_no_push_when_no_patient_phone(self, mock_service_cls):
        self.patient_record.phone = ""
        self.patient_record.save()
        mock_service = mock_service_cls.return_value
        response = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/summary/send/",
            {"delivery_method": "app"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        mock_service.send_push_notification.assert_not_called()

    @patch("apps.summaries.views.NotificationService")
    def test_send_summary_push_failure_does_not_break_response(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.send_push_notification.side_effect = Exception("FCM error")
        response = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/summary/send/",
            {"delivery_method": "app"},
            format="json",
        )
        # Should still return 200 even if push notification fails
        assert response.status_code == status.HTTP_200_OK
        self.summary.refresh_from_db()
        assert self.summary.delivery_status == "sent"
