import uuid

import pytest
from django.test import TestCase

from apps.accounts.models import Practice, User


class UserModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Test Clinic",
            subscription_tier="solo",
        )

    def test_create_doctor_user(self):
        user = User.objects.create_user(
            email="doctor@example.com",
            password="securepassword123!",
            first_name="Jane",
            last_name="Smith",
            role="doctor",
            practice=self.practice,
        )
        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.email == "doctor@example.com"
        assert user.role == "doctor"
        assert user.practice == self.practice
        assert user.check_password("securepassword123!")

    def test_create_patient_user(self):
        user = User.objects.create_user(
            email="patient@example.com",
            password=None,
            first_name="John",
            last_name="Doe",
            role="patient",
            phone="+15551234567",
        )
        assert user.role == "patient"
        assert not user.has_usable_password()

    def test_create_admin_user(self):
        user = User.objects.create_user(
            email="admin@example.com",
            password="securepassword123!",
            first_name="Admin",
            last_name="User",
            role="admin",
            practice=self.practice,
        )
        assert user.role == "admin"

    def test_user_str(self):
        user = User.objects.create_user(
            email="doctor@example.com",
            password="securepassword123!",
            first_name="Jane",
            last_name="Smith",
            role="doctor",
            practice=self.practice,
        )
        assert str(user) == "doctor@example.com"

    def test_user_has_uuid_pk(self):
        user = User.objects.create_user(
            email="doctor@example.com",
            password="test",
            role="doctor",
            practice=self.practice,
        )
        assert isinstance(user.pk, uuid.UUID)

    def test_email_is_unique(self):
        User.objects.create_user(
            email="unique@example.com", password="test", role="doctor", practice=self.practice
        )
        with pytest.raises(Exception):
            User.objects.create_user(
                email="unique@example.com", password="test2", role="doctor", practice=self.practice
            )

    def test_role_choices_enforced(self):
        user = User(email="bad@example.com", role="hacker")
        with pytest.raises(Exception):
            user.full_clean()


class PracticeModelTest(TestCase):
    def test_create_practice(self):
        practice = Practice.objects.create(
            name="Downtown Clinic",
            subscription_tier="group",
        )
        assert practice.id is not None
        assert isinstance(practice.id, uuid.UUID)
        assert practice.name == "Downtown Clinic"
        assert practice.subscription_tier == "group"

    def test_practice_str(self):
        practice = Practice.objects.create(name="My Clinic", subscription_tier="solo")
        assert str(practice) == "My Clinic"

    def test_practice_white_label_config_nullable(self):
        practice = Practice.objects.create(
            name="Test",
            subscription_tier="solo",
            white_label_config=None,
        )
        assert practice.white_label_config is None

    def test_practice_with_white_label_config(self):
        config = {
            "logo_url": "https://cdn.example.com/logo.png",
            "brand_color": "#FF5733",
            "custom_domain": "portal.clinic.com",
            "widget_key": "wk_abc123",
        }
        practice = Practice.objects.create(
            name="Branded Clinic",
            subscription_tier="enterprise",
            white_label_config=config,
        )
        assert practice.white_label_config["brand_color"] == "#FF5733"
