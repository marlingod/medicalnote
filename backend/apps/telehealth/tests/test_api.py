from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.patients.models import Patient
from apps.telehealth.models import StateComplianceRule, TelehealthEncounter


class TelehealthAPITest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Tele API Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="tele_api@test.com",
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
        StateComplianceRule.objects.create(
            state_code="FL",
            state_name="Florida",
            consent_type="verbal",
            consent_required=True,
            consent_statute="FL Stat. 456.47",
            recording_consent="one_party",
            interstate_compact=True,
        )
        StateComplianceRule.objects.create(
            state_code="NY",
            state_name="New York",
            consent_type="written",
            consent_required=True,
            consent_statute="NY PHL 2999-cc",
            recording_consent="one_party",
            interstate_compact=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor)

    def test_create_telehealth_encounter(self):
        resp = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/telehealth/",
            {
                "patient_location_state": "FL",
                "patient_location_city": "Jacksonville",
                "patient_location_setting": "home",
                "provider_location_state": "NY",
                "provider_location_city": "New York",
                "modality": "audio_video",
                "platform": "Zoom for Healthcare",
                "consent_obtained": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["pos_code"], "10")
        self.assertEqual(resp.data["cpt_modifier"], "-95")
        self.assertEqual(resp.data["consent_statute"], "FL Stat. 456.47")
        self.assertIsInstance(resp.data["compliance_warnings"], list)

    def test_get_telehealth_encounter(self):
        TelehealthEncounter.objects.create(
            encounter=self.encounter,
            patient_location_state="FL",
            provider_location_state="NY",
            modality="audio_video",
            pos_code="10",
            cpt_modifier="-95",
        )
        resp = self.client.get(
            f"/api/v1/encounters/{self.encounter.id}/telehealth/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["patient_location_state"], "FL")

    def test_update_telehealth_encounter(self):
        TelehealthEncounter.objects.create(
            encounter=self.encounter,
            patient_location_state="FL",
            provider_location_state="NY",
            modality="audio_video",
        )
        resp = self.client.patch(
            f"/api/v1/encounters/{self.encounter.id}/telehealth/update/",
            {"technology_adequate": False, "technology_notes": "Low bandwidth"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["technology_adequate"])

    def test_compliance_check(self):
        resp = self.client.post(
            "/api/v1/telehealth/compliance/check/",
            {
                "patient_state": "FL",
                "provider_state": "NY",
                "patient_setting": "home",
                "modality": "audio_video",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["pos_code"], "10")
        self.assertEqual(resp.data["cpt_modifier"], "-95")

    def test_list_state_rules(self):
        resp = self.client.get("/api/v1/telehealth/states/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_get_state_rule(self):
        resp = self.client.get("/api/v1/telehealth/states/FL/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["state_code"], "FL")

    def test_get_telehealth_not_found(self):
        resp = self.client.get(
            f"/api/v1/encounters/{self.encounter.id}/telehealth/"
        )
        self.assertEqual(resp.status_code, 404)
