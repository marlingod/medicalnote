from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.quality.models import QualityScore
from apps.telehealth.models import StateComplianceRule, TelehealthEncounter


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION="none",
)
class TelehealthFullPipelineTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Tele E2E Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="tele_e2e@test.com",
            password="TeleP@ss1!",
            role="doctor",
            first_name="Tele",
            last_name="Doc",
            practice=self.practice,
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="Tele",
            last_name="Patient",
            date_of_birth=date(1985, 7, 15),
        )
        PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="p",
            is_active=True,
        )
        PromptVersion.objects.create(
            prompt_name="patient_summary",
            version="1.0.0",
            template_text="p",
            is_active=True,
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
        self.api = APIClient()
        self.api.force_authenticate(user=self.doctor)

    @patch("workers.quality_checker._send_ws_update")
    @patch("workers.summary.LLMService")
    @patch("workers.soap_note.LLMService")
    def test_telehealth_encounter_full_flow(
        self, mock_soap_cls, mock_summary_cls, mock_ws
    ):
        mock_soap = MagicMock()
        mock_soap_cls.return_value = mock_soap
        mock_soap.generate_soap_note.return_value = {
            "subjective": (
                "Patient reports HTN follow-up. BP at home 138/86. "
                "No headaches, dizziness, or chest pain."
            ),
            "objective": (
                "Physical exam limited to visual inspection via video. "
                "Well-appearing. Constitutional: no acute distress."
            ),
            "assessment": (
                "1. Essential hypertension (I10) - suboptimally controlled. "
                "Medical decision making: moderate complexity."
            ),
            "plan": (
                "1. Increase lisinopril to 40mg daily. "
                "2. Labs in 2 weeks. "
                "3. Follow up 4 weeks."
            ),
            "icd10_codes": ["I10"],
            "cpt_codes": ["99214"],
        }
        mock_summary = MagicMock()
        mock_summary_cls.return_value = mock_summary
        mock_summary.generate_patient_summary.return_value = {
            "summary_en": "Your blood pressure is a bit high.",
            "summary_es": "",
            "medical_terms_explained": [],
        }

        # Step 1: Create encounter
        enc_resp = self.api.post(
            "/api/v1/encounters/",
            {
                "patient": str(self.patient.id),
                "encounter_date": "2026-03-16",
                "input_method": "telehealth",
            },
            format="json",
        )
        self.assertEqual(enc_resp.status_code, 201)
        encounter_id = enc_resp.data["id"]

        # Step 2: Add telehealth metadata
        tele_resp = self.api.post(
            f"/api/v1/encounters/{encounter_id}/telehealth/",
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
        self.assertEqual(tele_resp.status_code, 201)
        self.assertEqual(tele_resp.data["pos_code"], "10")
        self.assertEqual(tele_resp.data["cpt_modifier"], "-95")
        self.assertIn("FL Stat. 456.47", tele_resp.data["consent_statute"])

        # Step 3: Paste clinical text (triggers SOAP + summary + quality)
        paste_resp = self.api.post(
            f"/api/v1/encounters/{encounter_id}/paste/",
            {
                "text": (
                    "Patient is a 58yo male for HTN follow-up via "
                    "telehealth. Home BP 138/86. Lisinopril 20mg. "
                    "Denies headaches."
                ),
            },
            format="json",
        )
        self.assertEqual(paste_resp.status_code, 202)

        # Step 4: Verify pipeline completed
        encounter = Encounter.objects.get(id=encounter_id)
        self.assertEqual(encounter.status, "ready_for_review")
        self.assertTrue(hasattr(encounter, "clinical_note"))
        self.assertTrue(hasattr(encounter, "patient_summary"))
        self.assertTrue(hasattr(encounter, "telehealth"))

        # Step 5: Verify quality score exists
        self.assertTrue(
            QualityScore.objects.filter(encounter=encounter).exists()
        )
        score = encounter.quality_score
        self.assertGreater(score.overall_score, 0)

        # Step 6: Verify encounter detail
        detail_resp = self.api.get(f"/api/v1/encounters/{encounter_id}/")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertTrue(detail_resp.data["has_note"])
        self.assertTrue(detail_resp.data["has_summary"])
        self.assertTrue(detail_resp.data["has_telehealth"])
        self.assertTrue(detail_resp.data["has_quality_score"])
