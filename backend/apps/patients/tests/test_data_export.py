import uuid

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User


class PatientDataExportTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com",
            password="SecurePass123!@#",
            role="doctor",
            practice=self.practice,
        )

    def test_export_returns_202(self):
        self.client.force_authenticate(user=self.doctor)
        patient_id = str(uuid.uuid4())
        response = self.client.post(
            "/api/v1/patients/export/",
            {"patient_id": patient_id},
            format="json",
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["status"] == "queued"
        assert response.data["patient_id"] == patient_id

    def test_export_unauthenticated_returns_401_or_403(self):
        response = self.client.post(
            "/api/v1/patients/export/",
            {"patient_id": str(uuid.uuid4())},
            format="json",
        )
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_export_invalid_patient_id_returns_400(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            "/api/v1/patients/export/",
            {"patient_id": "not-a-uuid"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_export_missing_patient_id_returns_400(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            "/api/v1/patients/export/",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
