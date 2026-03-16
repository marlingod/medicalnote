import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default consent rules for states not in the database
DEFAULT_CONSENT = {
    "consent_required": True,
    "consent_type": "verbal",
    "consent_statute": "Check applicable state law",
    "recording_consent": "one_party",
}


class ComplianceService:
    """Multi-state telehealth compliance engine."""

    def determine_pos_code(self, patient_setting: str) -> str:
        """Determine Place of Service code based on patient location setting."""
        if patient_setting in ("home", "office", "other"):
            return "10"  # Telehealth in patient home
        elif patient_setting == "facility":
            return "02"  # Telehealth in facility
        return "10"  # Default to home

    def determine_cpt_modifier(self, modality: str) -> str:
        """Determine CPT modifier based on telehealth modality."""
        if modality == "audio_video":
            return "-95"  # Synchronous telehealth
        elif modality == "audio_only":
            return "-95"  # Also -95 per current CMS guidance
        elif modality == "store_forward":
            return "-GQ"  # Asynchronous telehealth
        return "-95"

    def get_consent_requirements(self, state_code: str) -> dict[str, Any]:
        """Get telehealth consent requirements for a state."""
        from apps.telehealth.models import StateComplianceRule

        try:
            rule = StateComplianceRule.objects.get(
                state_code=state_code, is_active=True
            )
            return {
                "consent_required": rule.consent_required,
                "consent_type": rule.consent_type,
                "consent_statute": rule.consent_statute,
                "prescribing_restrictions": rule.prescribing_restrictions,
                "medicaid_coverage": rule.medicaid_coverage,
                "interstate_compact": rule.interstate_compact,
            }
        except StateComplianceRule.DoesNotExist:
            logger.warning(
                f"No compliance rule found for state {state_code}, "
                f"using defaults"
            )
            return DEFAULT_CONSENT.copy()

    def check_recording_consent(
        self, patient_state: str, provider_state: str
    ) -> dict[str, Any]:
        """Determine recording consent requirement (most restrictive wins)."""
        from apps.telehealth.models import StateComplianceRule

        consent_level = "one_party"
        for state_code in [patient_state, provider_state]:
            try:
                rule = StateComplianceRule.objects.get(
                    state_code=state_code, is_active=True
                )
                if rule.recording_consent == "two_party":
                    consent_level = "two_party"
            except StateComplianceRule.DoesNotExist:
                pass

        return {
            "recording_consent": consent_level,
            "requires_all_party_consent": consent_level == "two_party",
        }

    def generate_compliance_report(
        self,
        patient_state: str,
        provider_state: str,
        patient_setting: str,
        modality: str,
    ) -> dict[str, Any]:
        """Generate a full compliance report for a telehealth encounter."""
        warnings = []

        pos_code = self.determine_pos_code(patient_setting)
        cpt_modifier = self.determine_cpt_modifier(modality)
        consent = self.get_consent_requirements(patient_state)
        recording = self.check_recording_consent(patient_state, provider_state)

        # Cross-state warnings
        if patient_state != provider_state:
            from apps.telehealth.models import StateComplianceRule

            try:
                patient_rule = StateComplianceRule.objects.get(
                    state_code=patient_state, is_active=True
                )
                if not patient_rule.interstate_compact:
                    warnings.append(
                        f"Cross-state telehealth: {patient_state} is NOT in "
                        f"the Interstate Medical Licensure Compact. Verify "
                        f"provider is licensed in {patient_state}."
                    )
                else:
                    warnings.append(
                        f"Cross-state telehealth: {patient_state} IS in the "
                        f"Interstate Compact. Verify compact license is active."
                    )
            except StateComplianceRule.DoesNotExist:
                warnings.append(
                    f"Cross-state telehealth: No compliance rules found for "
                    f"{patient_state}. Verify licensing requirements manually."
                )

        # Recording consent warning
        if recording["requires_all_party_consent"]:
            warnings.append(
                "Two-party (all-party) recording consent required. "
                "Ensure explicit consent from all participants before "
                "recording."
            )

        # Prescribing restrictions
        if consent.get("prescribing_restrictions"):
            warnings.append(
                f"Prescribing restriction ({patient_state}): "
                f"{consent['prescribing_restrictions']}"
            )

        # Audio-only warnings
        if modality == "audio_only":
            warnings.append(
                "Audio-only visit: Physical exam is limited to patient "
                "verbal report only. Document exam limitations accordingly."
            )

        return {
            "pos_code": pos_code,
            "cpt_modifier": cpt_modifier,
            "consent": consent,
            "recording_consent": recording,
            "warnings": warnings,
        }
