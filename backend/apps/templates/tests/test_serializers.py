from unittest.mock import MagicMock
from django.test import TestCase, RequestFactory
from apps.accounts.models import Practice, User
from apps.templates.models import NoteTemplate, TemplateRating, TemplateFavorite
from apps.templates.serializers import (
    NoteTemplateListSerializer,
    NoteTemplateDetailSerializer,
    NoteTemplateCreateSerializer,
    TemplateRatingSerializer,
)


class NoteTemplateListSerializerTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Test Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="testpass123!", role="doctor",
            practice=self.practice, last_name="Smith",
        )
        self.template = NoteTemplate.objects.create(
            name="Test Template",
            description="A test desc",
            specialty="primary_care",
            note_type="soap",
            schema={"sections": []},
            created_by=self.doctor,
            practice=self.practice,
            visibility="public",
            status="published",
            tags=["test-tag"],
        )
        self.factory = RequestFactory()

    def test_template_list_serializer_fields(self):
        request = self.factory.get("/")
        request.user = self.doctor
        serializer = NoteTemplateListSerializer(
            self.template, context={"request": request}
        )
        data = serializer.data
        assert data["id"] is not None
        assert data["name"] == "Test Template"
        assert data["specialty"] == "primary_care"
        assert data["note_type"] == "soap"
        assert data["visibility"] == "public"
        assert data["status"] == "published"
        assert data["tags"] == ["test-tag"]
        assert data["author_name"] == "Dr. Smith"
        assert "schema" not in data  # list serializer does not include schema

    def test_average_rating_calculation(self):
        request = self.factory.get("/")
        request.user = self.doctor
        doc2 = User.objects.create_user(
            email="doc2@test.com", password="testpass123!", role="doctor", practice=self.practice
        )
        TemplateRating.objects.create(template=self.template, user=self.doctor, score=4)
        TemplateRating.objects.create(template=self.template, user=doc2, score=2)
        serializer = NoteTemplateListSerializer(
            self.template, context={"request": request}
        )
        assert serializer.data["average_rating"] == 3.0
        assert serializer.data["rating_count"] == 2

    def test_is_favorited(self):
        request = self.factory.get("/")
        request.user = self.doctor
        serializer = NoteTemplateListSerializer(
            self.template, context={"request": request}
        )
        assert serializer.data["is_favorited"] is False

        TemplateFavorite.objects.create(template=self.template, user=self.doctor)
        serializer = NoteTemplateListSerializer(
            self.template, context={"request": request}
        )
        assert serializer.data["is_favorited"] is True


class NoteTemplateDetailSerializerTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Test Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="testpass123!", role="doctor",
            practice=self.practice,
        )
        self.template = NoteTemplate.objects.create(
            name="Detail Template",
            specialty="dermatology",
            schema={"sections": [{"key": "subjective", "label": "S", "fields": []}]},
            created_by=self.doctor,
        )
        self.factory = RequestFactory()

    def test_template_detail_serializer_includes_schema(self):
        request = self.factory.get("/")
        request.user = self.doctor
        serializer = NoteTemplateDetailSerializer(
            self.template, context={"request": request}
        )
        data = serializer.data
        assert "schema" in data
        assert data["schema"]["sections"][0]["key"] == "subjective"
        assert "ratings" in data


class NoteTemplateCreateSerializerTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Test Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="testpass123!", role="doctor",
            practice=self.practice,
        )
        self.factory = RequestFactory()

    def test_template_create_serializer_sets_created_by(self):
        request = self.factory.post("/")
        request.user = self.doctor
        data = {
            "name": "New Template",
            "specialty": "general",
            "note_type": "soap",
            "schema": {"sections": []},
        }
        serializer = NoteTemplateCreateSerializer(data=data, context={"request": request})
        assert serializer.is_valid(), serializer.errors
        template = serializer.save()
        assert template.created_by == self.doctor
        assert template.practice == self.practice
