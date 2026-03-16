from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import Practice, User
from apps.templates.models import NoteTemplate, TemplateRating, TemplateFavorite


class NoteTemplateViewSetTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Test Clinic", subscription_tier="solo")
        self.practice2 = Practice.objects.create(name="Other Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="testpass123!", role="doctor",
            practice=self.practice, last_name="Smith",
        )
        self.doctor2 = User.objects.create_user(
            email="doc2@test.com", password="testpass123!", role="doctor",
            practice=self.practice2, last_name="Jones",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor)

        # Create templates
        self.own_template = NoteTemplate.objects.create(
            name="My Template",
            specialty="general",
            schema={"sections": [{"key": "subjective", "label": "S", "fields": []}]},
            created_by=self.doctor,
            practice=self.practice,
            visibility="private",
            status="draft",
        )
        self.public_template = NoteTemplate.objects.create(
            name="Public Template",
            specialty="primary_care",
            schema={"sections": []},
            created_by=self.doctor2,
            practice=self.practice2,
            visibility="public",
            status="published",
        )
        self.private_other = NoteTemplate.objects.create(
            name="Other Private",
            specialty="dermatology",
            schema={},
            created_by=self.doctor2,
            practice=self.practice2,
            visibility="private",
            status="draft",
        )

    def test_list_templates_returns_own_and_public(self):
        resp = self.client.get("/api/v1/templates/")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.data["results"]]
        assert "My Template" in names
        assert "Public Template" in names
        assert "Other Private" not in names

    def test_marketplace_scope_filter(self):
        resp = self.client.get("/api/v1/templates/?scope=marketplace")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.data["results"]]
        assert "Public Template" in names
        assert "My Template" not in names

    def test_create_template(self):
        resp = self.client.post("/api/v1/templates/", {
            "name": "New Template",
            "specialty": "cardiology",
            "note_type": "soap",
            "schema": {"sections": []},
        }, format="json")
        assert resp.status_code == 201
        assert resp.data["name"] == "New Template"
        assert NoteTemplate.objects.filter(name="New Template").exists()

    def test_update_own_template(self):
        resp = self.client.patch(
            f"/api/v1/templates/{self.own_template.id}/",
            {"name": "Updated Template"},
            format="json",
        )
        assert resp.status_code == 200
        self.own_template.refresh_from_db()
        assert self.own_template.name == "Updated Template"

    def test_delete_own_template(self):
        resp = self.client.delete(f"/api/v1/templates/{self.own_template.id}/")
        assert resp.status_code == 204
        assert not NoteTemplate.objects.filter(id=self.own_template.id).exists()

    def test_cannot_delete_others_template(self):
        resp = self.client.delete(f"/api/v1/templates/{self.public_template.id}/")
        assert resp.status_code == 403

    def test_clone_template(self):
        resp = self.client.post(
            f"/api/v1/templates/{self.public_template.id}/clone/",
            {"name": "My Clone"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["name"] == "My Clone"
        cloned = NoteTemplate.objects.get(name="My Clone")
        assert cloned.created_by == self.doctor
        assert cloned.parent_template == self.public_template
        assert cloned.visibility == "private"
        self.public_template.refresh_from_db()
        assert self.public_template.clone_count == 1

    def test_rate_template(self):
        resp = self.client.post(
            f"/api/v1/templates/{self.public_template.id}/rate/",
            {"score": 4, "review": "Great template"},
            format="json",
        )
        assert resp.status_code == 201
        assert TemplateRating.objects.filter(
            template=self.public_template, user=self.doctor
        ).exists()

    def test_rate_template_update_existing(self):
        TemplateRating.objects.create(
            template=self.public_template, user=self.doctor, score=3
        )
        resp = self.client.post(
            f"/api/v1/templates/{self.public_template.id}/rate/",
            {"score": 5},
            format="json",
        )
        assert resp.status_code == 200
        rating = TemplateRating.objects.get(template=self.public_template, user=self.doctor)
        assert rating.score == 5

    def test_toggle_favorite(self):
        # Favorite
        resp = self.client.post(f"/api/v1/templates/{self.public_template.id}/favorite/")
        assert resp.status_code == 200
        assert resp.data["favorited"] is True
        assert TemplateFavorite.objects.filter(
            template=self.public_template, user=self.doctor
        ).exists()

        # Unfavorite
        resp = self.client.delete(f"/api/v1/templates/{self.public_template.id}/favorite/")
        assert resp.status_code == 200
        assert resp.data["favorited"] is False

    def test_list_specialties(self):
        resp = self.client.get("/api/v1/templates/specialties/")
        assert resp.status_code == 200
        specialties = resp.data
        assert isinstance(specialties, list)
        primary_care = next((s for s in specialties if s["value"] == "primary_care"), None)
        assert primary_care is not None
        assert primary_care["template_count"] == 1  # The public published template

    def test_list_favorites(self):
        TemplateFavorite.objects.create(template=self.public_template, user=self.doctor)
        resp = self.client.get("/api/v1/templates/favorites/")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.data]
        assert "Public Template" in names

    @patch("services.template_llm_service.TemplateLLMService")
    def test_auto_complete_endpoint(self, mock_llm_cls):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.auto_complete_section.return_value = {
            "content": "Generated HPI content",
            "confidence": 0.9,
            "suggestions": [],
        }
        resp = self.client.post(
            f"/api/v1/templates/{self.own_template.id}/auto-complete/",
            {"section_key": "subjective", "field_key": "hpi"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["content"] == "Generated HPI content"

    def test_unauthenticated_access_denied(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get("/api/v1/templates/")
        assert resp.status_code in (401, 403)

    def test_patient_access_denied(self):
        patient = User.objects.create_user(
            email="patient@test.com", password="testpass123!", role="patient"
        )
        self.client.force_authenticate(user=patient)
        resp = self.client.get("/api/v1/templates/")
        assert resp.status_code == 403
