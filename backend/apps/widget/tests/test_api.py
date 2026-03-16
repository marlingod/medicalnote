from datetime import date
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


class WidgetAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.practice = Practice.objects.create(
            name="Clinic", subscription_tier="enterprise",
            white_label_config={
                "logo_url": "https://cdn.example.com/logo.png",
                "brand_color": "#FF5733",
                "widget_key": "wk_test123",
            },
        )

    def test_get_widget_config(self):
        response = self.client.get("/api/v1/widget/config/wk_test123/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["brand_color"] == "#FF5733"

    def test_widget_config_invalid_key(self):
        response = self.client.get("/api/v1/widget/config/wk_invalid/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
