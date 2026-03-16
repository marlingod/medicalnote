import uuid

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import DeviceToken, User


class DeviceTokenModelTest(TestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            email="patient@test.com", role="patient", phone="+15551234567"
        )

    def test_create_device_token(self):
        dt = DeviceToken.objects.create(
            user=self.patient_user, token="fcm-token-abc", platform="ios"
        )
        assert dt.id is not None
        assert isinstance(dt.id, uuid.UUID)
        assert dt.token == "fcm-token-abc"
        assert dt.platform == "ios"
        assert dt.is_active is True

    def test_device_token_str(self):
        dt = DeviceToken.objects.create(
            user=self.patient_user, token="fcm-token-abc", platform="android"
        )
        assert "android" in str(dt)
        assert self.patient_user.email in str(dt)

    def test_token_unique_constraint(self):
        DeviceToken.objects.create(
            user=self.patient_user, token="same-token", platform="ios"
        )
        other_user = User.objects.create_user(
            email="other@test.com", role="patient", phone="+15559999999"
        )
        with self.assertRaises(Exception):
            DeviceToken.objects.create(
                user=other_user, token="same-token", platform="android"
            )


class DeviceTokenAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient_user = User.objects.create_user(
            email="patient@test.com", role="patient", phone="+15551234567"
        )
        self.doctor_user = User.objects.create_user(
            email="doc@test.com", password="test", role="doctor"
        )

    def test_register_device_token_creates_new(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.post(
            "/api/v1/patient/device/",
            {"token": "fcm-token-123", "platform": "ios"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["token"] == "fcm-token-123"
        assert response.data["platform"] == "ios"
        assert DeviceToken.objects.filter(user=self.patient_user).count() == 1

    def test_register_device_token_updates_existing(self):
        self.client.force_authenticate(user=self.patient_user)
        # First registration
        self.client.post(
            "/api/v1/patient/device/",
            {"token": "fcm-token-123", "platform": "ios"},
            format="json",
        )
        # Same token, update platform
        response = self.client.post(
            "/api/v1/patient/device/",
            {"token": "fcm-token-123", "platform": "android"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["platform"] == "android"
        assert DeviceToken.objects.filter(user=self.patient_user).count() == 1

    def test_register_device_token_requires_patient_role(self):
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.post(
            "/api/v1/patient/device/",
            {"token": "fcm-token-123", "platform": "ios"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_register_device_token_requires_auth(self):
        response = self.client.post(
            "/api/v1/patient/device/",
            {"token": "fcm-token-123", "platform": "ios"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_register_device_token_invalid_platform(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.post(
            "/api/v1/patient/device/",
            {"token": "fcm-token-123", "platform": "windows"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_device_token_missing_fields(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.post(
            "/api/v1/patient/device/",
            {"token": "fcm-token-123"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
