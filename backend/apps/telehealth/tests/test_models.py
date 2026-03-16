import uuid
from datetime import date

from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.patients.models import Patient
from apps.telehealth.models import StateComplianceRule, TelehealthEncounter


class TelehealthEncounterModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Tele Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="tele_doc@test.com",
            password="test",
            role="doctor",
            practice=self.practice,
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="T",
            last_name="P",
            date_of_birth="1990-01-01",
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="recording",
            status="uploading",
        )

    def test_create_telehealth_encounter(self):
        tele = TelehealthEncounter.objects.create(
            encounter=self.encounter,
            patient_location_state="FL",
            patient_location_city="Jacksonville",
            patient_location_setting="home",
            provider_location_state="NY",
            provider_location_city="New York",
            modality="audio_video",
            platform="Zoom for Healthcare",
            consent_type="verbal",
            consent_obtained=True,
            consent_statute="FL Stat. 456.47",
            pos_code="10",
            cpt_modifier="-95",
            technology_adequate=True,
        )
        assert tele.id is not None
        assert isinstance(tele.id, uuid.UUID)
        assert tele.patient_location_state == "FL"
        assert tele.pos_code == "10"

    def test_telehealth_one_per_encounter(self):
        TelehealthEncounter.objects.create(
            encounter=self.encounter,
            patient_location_state="FL",
            provider_location_state="NY",
            modality="audio_video",
        )
        tele, created = TelehealthEncounter.objects.update_or_create(
            encounter=self.encounter,
            defaults={
                "patient_location_state": "CA",
                "provider_location_state": "NY",
                "modality": "audio_only",
            },
        )
        assert not created
        assert tele.patient_location_state == "CA"

    def test_telehealth_str(self):
        tele = TelehealthEncounter.objects.create(
            encounter=self.encounter,
            patient_location_state="FL",
            modality="audio_video",
        )
        assert "audio_video" in str(tele)


class StateComplianceRuleModelTest(TestCase):
    def test_create_state_rule(self):
        rule = StateComplianceRule.objects.create(
            state_code="FL",
            state_name="Florida",
            consent_type="verbal",
            consent_required=True,
            consent_statute="FL Stat. 456.47",
            recording_consent="one_party",
            prescribing_restrictions=(
                "No controlled substances via telehealth "
                "without prior in-person visit"
            ),
            interstate_compact=True,
            medicaid_coverage=True,
            additional_rules={
                "min_age_without_parent": 18,
                "mental_health_parity": True,
            },
        )
        assert rule.id is not None
        assert rule.state_code == "FL"
        assert rule.consent_type == "verbal"

    def test_state_code_unique(self):
        StateComplianceRule.objects.create(
            state_code="FL", state_name="Florida"
        )
        with self.assertRaises(IntegrityError):
            StateComplianceRule.objects.create(
                state_code="FL", state_name="Florida 2"
            )

    def test_state_rule_str(self):
        rule = StateComplianceRule.objects.create(
            state_code="NY", state_name="New York"
        )
        assert "NY" in str(rule)
        assert "New York" in str(rule)
