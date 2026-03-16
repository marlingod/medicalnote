from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User


class PatientProfileAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient_user = User.objects.create_user(
            email="patient@test.com",
            role="patient",
            phone="+15551234567",
            first_name="Jane",
            last_name="Doe",
            language_preference="en",
        )
        self.doctor_user = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor"
        )

    def test_get_profile(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get("/api/v1/patient/profile/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Jane"
        assert response.data["last_name"] == "Doe"
        assert response.data["phone"] == "+15551234567"
        assert response.data["language_preference"] == "en"
        assert response.data["email"] == "patient@test.com"

    def test_patch_profile_name(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.patch(
            "/api/v1/patient/profile/",
            {"first_name": "Janet", "last_name": "Smith"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Janet"
        assert response.data["last_name"] == "Smith"
        self.patient_user.refresh_from_db()
        assert self.patient_user.first_name == "Janet"
        assert self.patient_user.last_name == "Smith"

    def test_patch_profile_language(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.patch(
            "/api/v1/patient/profile/",
            {"language_preference": "es"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["language_preference"] == "es"
        self.patient_user.refresh_from_db()
        assert self.patient_user.language_preference == "es"

    def test_patch_profile_phone_is_read_only(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.patch(
            "/api/v1/patient/profile/",
            {"phone": "+19999999999"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        self.patient_user.refresh_from_db()
        assert self.patient_user.phone == "+15551234567"

    def test_patch_profile_email_is_read_only(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.patch(
            "/api/v1/patient/profile/",
            {"email": "newemail@test.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        self.patient_user.refresh_from_db()
        assert self.patient_user.email == "patient@test.com"

    def test_profile_requires_patient_role(self):
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get("/api/v1/patient/profile/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_profile_requires_auth(self):
        response = self.client.get("/api/v1/patient/profile/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
