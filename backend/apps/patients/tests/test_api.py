from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.patients.models import Patient


class PatientAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor", practice=self.practice
        )
        self.other_practice = Practice.objects.create(name="Other Clinic", subscription_tier="solo")
        self.other_doctor = User.objects.create_user(
            email="other@test.com", password="test", role="doctor", practice=self.other_practice
        )
        self.client.force_authenticate(user=self.doctor)

    def test_create_patient(self):
        response = self.client.post(
            "/api/v1/patients/",
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "email": "john@example.com",
                "phone": "+15551234567",
                "language_preference": "en",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["first_name"] == "John"

    def test_list_patients_filtered_by_practice(self):
        Patient.objects.create(
            practice=self.practice, first_name="A", last_name="B", date_of_birth="1990-01-01"
        )
        Patient.objects.create(
            practice=self.other_practice, first_name="C", last_name="D", date_of_birth="1990-01-01"
        )
        response = self.client.get("/api/v1/patients/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_get_patient_detail(self):
        patient = Patient.objects.create(
            practice=self.practice, first_name="A", last_name="B", date_of_birth="1990-01-01"
        )
        response = self.client.get(f"/api/v1/patients/{patient.id}/")
        assert response.status_code == status.HTTP_200_OK

    def test_cannot_access_other_practice_patient(self):
        patient = Patient.objects.create(
            practice=self.other_practice, first_name="X", last_name="Y", date_of_birth="1990-01-01"
        )
        response = self.client.get(f"/api/v1/patients/{patient.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_patient(self):
        patient = Patient.objects.create(
            practice=self.practice, first_name="A", last_name="B", date_of_birth="1990-01-01"
        )
        response = self.client.patch(
            f"/api/v1/patients/{patient.id}/",
            {"language_preference": "es"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        patient.refresh_from_db()
        assert patient.language_preference == "es"

    def test_unauthenticated_access_denied(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/patients/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_patient_role_cannot_list_patients(self):
        patient_user = User.objects.create_user(
            email="patient@test.com", role="patient"
        )
        self.client.force_authenticate(user=patient_user)
        response = self.client.get("/api/v1/patients/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
