from django.test import TestCase
from apps.accounts.models import Practice, User
from apps.templates.specialty_configs import (
    PRIMARY_CARE_TEMPLATES,
    DERMATOLOGY_TEMPLATES,
    PSYCHIATRY_TEMPLATES,
    ALL_SPECIALTY_TEMPLATES,
)


class SpecialtyConfigTest(TestCase):
    def _assert_template_has_valid_schema(self, template_data):
        """Helper to validate a template data dict has proper structure."""
        assert "name" in template_data
        assert "description" in template_data
        assert "specialty" in template_data
        assert "schema" in template_data
        schema = template_data["schema"]
        assert "sections" in schema
        assert len(schema["sections"]) > 0
        for section in schema["sections"]:
            assert "key" in section
            assert "label" in section
            assert "fields" in section

    def test_primary_care_templates_have_required_schema(self):
        assert len(PRIMARY_CARE_TEMPLATES) >= 1
        for t in PRIMARY_CARE_TEMPLATES:
            self._assert_template_has_valid_schema(t)
            assert t["specialty"] == "primary_care"
            # Should have SOAP sections
            section_keys = [s["key"] for s in t["schema"]["sections"]]
            assert "subjective" in section_keys
            assert "objective" in section_keys
            assert "assessment" in section_keys
            assert "plan" in section_keys

    def test_dermatology_templates_have_abcde_fields(self):
        assert len(DERMATOLOGY_TEMPLATES) >= 1
        for t in DERMATOLOGY_TEMPLATES:
            self._assert_template_has_valid_schema(t)
            assert t["specialty"] == "dermatology"
            # Check for ABCDE criteria in objective section
            objective = next(s for s in t["schema"]["sections"] if s["key"] == "objective")
            field_keys = [f["key"] for f in objective["fields"]]
            assert "abcde" in field_keys
            # Verify ABCDE subfields
            abcde_field = next(f for f in objective["fields"] if f["key"] == "abcde")
            subfield_keys = [sf["key"] for sf in abcde_field["subfields"]]
            assert "asymmetry" in subfield_keys
            assert "border" in subfield_keys
            assert "color" in subfield_keys
            assert "diameter" in subfield_keys
            assert "evolution" in subfield_keys

    def test_psychiatry_templates_have_mse_fields(self):
        assert len(PSYCHIATRY_TEMPLATES) >= 1
        for t in PSYCHIATRY_TEMPLATES:
            self._assert_template_has_valid_schema(t)
            assert t["specialty"] == "psychiatry"
            # Check for MSE fields in objective
            objective = next(s for s in t["schema"]["sections"] if s["key"] == "objective")
            field_keys = [f["key"] for f in objective["fields"]]
            # Must have key MSE elements
            assert "mood" in field_keys
            assert "affect" in field_keys
            assert "thought_process" in field_keys
            assert "suicidal_ideation" in field_keys
            assert "phq9_score" in field_keys
            assert "gad7_score" in field_keys

    def test_all_specialty_templates_combined(self):
        expected_count = (
            len(PRIMARY_CARE_TEMPLATES)
            + len(DERMATOLOGY_TEMPLATES)
            + len(PSYCHIATRY_TEMPLATES)
        )
        assert len(ALL_SPECIALTY_TEMPLATES) == expected_count

    def test_all_templates_have_tags(self):
        for t in ALL_SPECIALTY_TEMPLATES:
            assert "tags" in t
            assert len(t["tags"]) > 0

    def test_all_templates_have_ai_instructions(self):
        for t in ALL_SPECIALTY_TEMPLATES:
            assert "ai_instructions" in t["schema"]
            assert len(t["schema"]["ai_instructions"]) > 10

    def test_seed_command_creates_templates(self):
        """Test that the seed command works end-to-end."""
        from io import StringIO
        from django.core.management import call_command

        practice = Practice.objects.create(name="Test Clinic", subscription_tier="solo")
        admin = User.objects.create_user(
            email="admin@test.com", password="testpass123!", role="admin",
            practice=practice, is_staff=True, is_superuser=True,
        )

        out = StringIO()
        call_command("seed_templates", stdout=out)
        output = out.getvalue()

        from apps.templates.models import NoteTemplate
        assert NoteTemplate.objects.count() == len(ALL_SPECIALTY_TEMPLATES)
        assert "Created" in output

        # Running again should skip existing
        out2 = StringIO()
        call_command("seed_templates", stdout=out2)
        assert NoteTemplate.objects.count() == len(ALL_SPECIALTY_TEMPLATES)
        assert "Skipped" in out2.getvalue()
