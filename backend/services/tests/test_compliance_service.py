from django.test import TestCase

from apps.telehealth.models import StateComplianceRule
from services.compliance_service import ComplianceService


class ComplianceServiceTest(TestCase):
    def setUp(self):
        self.service = ComplianceService()
        StateComplianceRule.objects.create(
            state_code="FL",
            state_name="Florida",
            consent_type="verbal",
            consent_required=True,
            consent_statute="FL Stat. 456.47",
            recording_consent="one_party",
            prescribing_restrictions="No CS via telehealth without prior in-person",
            interstate_compact=True,
            medicaid_coverage=True,
        )
        StateComplianceRule.objects.create(
            state_code="CA",
            state_name="California",
            consent_type="verbal",
            consent_required=True,
            consent_statute="Cal. Bus. & Prof. Code 2290.5",
            recording_consent="two_party",
            prescribing_restrictions="",
            interstate_compact=False,
            medicaid_coverage=True,
        )
        StateComplianceRule.objects.create(
            state_code="NY",
            state_name="New York",
            consent_type="written",
            consent_required=True,
            consent_statute="NY PHL 2999-cc",
            recording_consent="one_party",
            prescribing_restrictions="",
            interstate_compact=True,
            medicaid_coverage=True,
        )

    def test_determine_pos_code_home(self):
        pos = self.service.determine_pos_code("home")
        assert pos == "10"

    def test_determine_pos_code_facility(self):
        pos = self.service.determine_pos_code("facility")
        assert pos == "02"

    def test_determine_cpt_modifier_audio_video(self):
        modifier = self.service.determine_cpt_modifier("audio_video")
        assert modifier == "-95"

    def test_determine_cpt_modifier_store_forward(self):
        modifier = self.service.determine_cpt_modifier("store_forward")
        assert modifier == "-GQ"

    def test_get_consent_requirements(self):
        result = self.service.get_consent_requirements("FL")
        assert result["consent_required"] is True
        assert result["consent_type"] == "verbal"
        assert "456.47" in result["consent_statute"]

    def test_get_consent_unknown_state(self):
        result = self.service.get_consent_requirements("ZZ")
        assert result["consent_required"] is True
        assert result["consent_type"] == "verbal"

    def test_check_recording_consent(self):
        result = self.service.check_recording_consent("FL", "NY")
        assert result["recording_consent"] == "one_party"

    def test_check_recording_consent_two_party_wins(self):
        result = self.service.check_recording_consent("CA", "NY")
        assert result["recording_consent"] == "two_party"

    def test_generate_compliance_report(self):
        report = self.service.generate_compliance_report(
            patient_state="FL",
            provider_state="NY",
            patient_setting="home",
            modality="audio_video",
        )
        assert report["pos_code"] == "10"
        assert report["cpt_modifier"] == "-95"
        assert report["consent"]["consent_required"] is True
        assert isinstance(report["warnings"], list)

    def test_compliance_report_cross_state_warning(self):
        report = self.service.generate_compliance_report(
            patient_state="CA",
            provider_state="NY",
            patient_setting="home",
            modality="audio_video",
        )
        warnings = report["warnings"]
        cross_state = [
            w
            for w in warnings
            if "interstate" in w.lower() or "cross-state" in w.lower()
        ]
        assert len(cross_state) > 0
