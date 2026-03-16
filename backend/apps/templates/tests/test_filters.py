import pytest
from django.test import TestCase, RequestFactory
from apps.accounts.models import Practice, User
from apps.templates.models import NoteTemplate
from apps.templates.filters import NoteTemplateFilter


class NoteTemplateFilterTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(name="Test Clinic", subscription_tier="solo")
        self.doctor = User.objects.create_user(
            email="doc@test.com", password="testpass123!", role="doctor", practice=self.practice
        )
        self.t1 = NoteTemplate.objects.create(
            name="Primary Care Template",
            description="For primary care visits",
            specialty="primary_care",
            note_type="soap",
            schema={},
            created_by=self.doctor,
            visibility="public",
            status="published",
            tags=["annual-physical", "wellness"],
        )
        self.t2 = NoteTemplate.objects.create(
            name="Dermatology Template",
            description="For skin assessments",
            specialty="dermatology",
            note_type="soap",
            schema={},
            created_by=self.doctor,
            visibility="private",
            status="draft",
            tags=["skin-lesion"],
        )
        self.t3 = NoteTemplate.objects.create(
            name="Psych Eval",
            description="Psychiatric initial evaluation template",
            specialty="psychiatry",
            note_type="soap",
            schema={},
            created_by=self.doctor,
            visibility="public",
            status="published",
            tags=["mental-health"],
        )

    def test_specialty_filter(self):
        f = NoteTemplateFilter({"specialty": "primary_care"}, queryset=NoteTemplate.objects.all())
        assert f.qs.count() == 1
        assert f.qs.first() == self.t1

    def test_search_filter(self):
        f = NoteTemplateFilter({"search": "skin"}, queryset=NoteTemplate.objects.all())
        assert f.qs.count() == 1
        assert f.qs.first() == self.t2

    def test_search_filter_by_name(self):
        f = NoteTemplateFilter({"search": "Psych"}, queryset=NoteTemplate.objects.all())
        assert f.qs.count() == 1
        assert f.qs.first() == self.t3

    @pytest.mark.skipif(
        "sqlite" in str(__import__("django").conf.settings.DATABASES["default"]["ENGINE"]),
        reason="JSONField __contains lookup not supported on SQLite",
    )
    def test_tag_filter(self):
        f = NoteTemplateFilter({"tag": "wellness"}, queryset=NoteTemplate.objects.all())
        assert f.qs.count() == 1
        assert f.qs.first() == self.t1

    def test_visibility_filter(self):
        f = NoteTemplateFilter({"visibility": "public"}, queryset=NoteTemplate.objects.all())
        assert f.qs.count() == 2

    def test_status_filter(self):
        f = NoteTemplateFilter({"status": "draft"}, queryset=NoteTemplate.objects.all())
        assert f.qs.count() == 1
        assert f.qs.first() == self.t2

    def test_combined_filters(self):
        f = NoteTemplateFilter(
            {"specialty": "primary_care", "status": "published"},
            queryset=NoteTemplate.objects.all(),
        )
        assert f.qs.count() == 1
        assert f.qs.first() == self.t1
