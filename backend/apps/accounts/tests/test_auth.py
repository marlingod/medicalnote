from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import Practice, User


class DoctorRegistrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_doctor_registration_creates_practice(self):
        response = self.client.post(
            "/api/v1/auth/registration/",
            {
                "email": "newdoc@example.com",
                "password1": "SecurePass123!@#",
                "password2": "SecurePass123!@#",
                "first_name": "Jane",
                "last_name": "Smith",
                "practice_name": "Smith Clinic",
                "specialty": "Internal Medicine",
            },
            format="json",
        )
        assert response.status_code in (status.HTTP_201_CREATED, status.HTTP_204_NO_CONTENT)
        user = User.objects.get(email="newdoc@example.com")
        assert user.role == "doctor"
        assert user.practice is not None
        assert user.practice.name == "Smith Clinic"

    def test_doctor_registration_requires_practice_name(self):
        response = self.client.post(
            "/api/v1/auth/registration/",
            {
                "email": "newdoc@example.com",
                "password1": "SecurePass123!@#",
                "password2": "SecurePass123!@#",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class DoctorLoginTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(name="Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doctor@example.com",
            password="SecurePass123!@#",
            role="doctor",
            practice=self.practice,
        )

    def test_login_returns_jwt(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "doctor@example.com", "password": "SecurePass123!@#"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data or "access_token" in response.data

    def test_login_wrong_password(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "doctor@example.com", "password": "wrongpassword"},
            format="json",
        )
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_get_current_user_authenticated(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get("/api/v1/auth/user/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "doctor@example.com"

    def test_get_current_user_unauthenticated(self):
        response = self.client.get("/api/v1/auth/user/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
