from django.db import IntegrityError
from django.test import TestCase
from apps.accounts.models import Practice, User
from apps.templates.models import NoteTemplate, TemplateRating, TemplateFavorite


class NoteTemplateModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Test Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="testpass123!", role="doctor", practice=self.practice
        )

    def test_create_note_template(self):
        template = NoteTemplate.objects.create(
            name="Test Template",
            description="A test template",
            specialty="primary_care",
            note_type="soap",
            schema={"sections": []},
            created_by=self.doctor,
            practice=self.practice,
        )
        assert template.id is not None
        assert template.name == "Test Template"
        assert template.specialty == "primary_care"
        assert template.visibility == "private"
        assert template.status == "draft"
        assert template.version == 1
        assert template.use_count == 0
        assert template.clone_count == 0

    def test_template_schema_json_field(self):
        schema = {
            "sections": [
                {
                    "key": "subjective",
                    "label": "Subjective",
                    "fields": [
                        {"key": "chief_complaint", "label": "CC", "type": "text", "required": True},
                    ],
                }
            ],
            "ai_instructions": "Test instructions",
        }
        template = NoteTemplate.objects.create(
            name="Schema Test",
            specialty="general",
            schema=schema,
            created_by=self.doctor,
        )
        template.refresh_from_db()
        assert template.schema == schema
        assert template.schema["sections"][0]["key"] == "subjective"
        assert template.schema["sections"][0]["fields"][0]["required"] is True

    def test_template_version_tracking(self):
        parent = NoteTemplate.objects.create(
            name="Parent Template",
            specialty="general",
            schema={"sections": []},
            created_by=self.doctor,
            version=1,
        )
        child = NoteTemplate.objects.create(
            name="Child Template",
            specialty="general",
            schema={"sections": []},
            created_by=self.doctor,
            parent_template=parent,
            version=2,
        )
        assert child.parent_template == parent
        assert child.version == 2
        assert parent.derived_templates.count() == 1
        assert parent.derived_templates.first() == child

    def test_template_str(self):
        template = NoteTemplate.objects.create(
            name="SOAP Template",
            specialty="dermatology",
            schema={},
            created_by=self.doctor,
        )
        assert str(template) == "SOAP Template (dermatology)"

    def test_template_ordering(self):
        t1 = NoteTemplate.objects.create(
            name="First", specialty="general", schema={}, created_by=self.doctor
        )
        t2 = NoteTemplate.objects.create(
            name="Second", specialty="general", schema={}, created_by=self.doctor
        )
        templates = list(NoteTemplate.objects.all())
        # Ordered by -updated_at, so most recent first
        assert templates[0] == t2
        assert templates[1] == t1


class TemplateRatingModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Test Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="testpass123!", role="doctor", practice=self.practice
        )
        self.doctor2 = User.objects.create_user(
            email="doc2@test.com", password="testpass123!", role="doctor", practice=self.practice
        )
        self.template = NoteTemplate.objects.create(
            name="Test Template",
            specialty="general",
            schema={},
            created_by=self.doctor,
        )

    def test_create_rating(self):
        rating = TemplateRating.objects.create(
            template=self.template, user=self.doctor, score=4, review="Good template"
        )
        assert rating.score == 4
        assert rating.review == "Good template"

    def test_template_rating_unique_per_user(self):
        TemplateRating.objects.create(
            template=self.template, user=self.doctor, score=4
        )
        with self.assertRaises(IntegrityError):
            TemplateRating.objects.create(
                template=self.template, user=self.doctor, score=5
            )

    def test_different_users_can_rate_same_template(self):
        TemplateRating.objects.create(
            template=self.template, user=self.doctor, score=4
        )
        TemplateRating.objects.create(
            template=self.template, user=self.doctor2, score=3
        )
        assert self.template.ratings.count() == 2

    def test_rating_str(self):
        rating = TemplateRating.objects.create(
            template=self.template, user=self.doctor, score=5
        )
        assert "5/5" in str(rating)
        assert "Test Template" in str(rating)


class TemplateFavoriteModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Test Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="testpass123!", role="doctor", practice=self.practice
        )
        self.template = NoteTemplate.objects.create(
            name="Test Template",
            specialty="general",
            schema={},
            created_by=self.doctor,
        )

    def test_template_favorite_toggle(self):
        # Favorite
        fav = TemplateFavorite.objects.create(template=self.template, user=self.doctor)
        assert fav.id is not None
        assert self.template.favorites.count() == 1

        # Unfavorite
        fav.delete()
        assert self.template.favorites.count() == 0

    def test_favorite_unique_per_user(self):
        TemplateFavorite.objects.create(template=self.template, user=self.doctor)
        with self.assertRaises(IntegrityError):
            TemplateFavorite.objects.create(template=self.template, user=self.doctor)
