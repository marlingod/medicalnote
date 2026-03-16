from rest_framework import serializers

from apps.telehealth.models import StateComplianceRule, TelehealthEncounter


class TelehealthEncounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelehealthEncounter
        fields = [
            "id",
            "encounter",
            "patient_location_state",
            "patient_location_city",
            "patient_location_setting",
            "provider_location_state",
            "provider_location_city",
            "modality",
            "platform",
            "consent_type",
            "consent_obtained",
            "consent_timestamp",
            "consent_statute",
            "pos_code",
            "cpt_modifier",
            "technology_adequate",
            "technology_notes",
            "compliance_warnings",
            "prescribing_restrictions_acknowledged",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "pos_code",
            "cpt_modifier",
            "consent_statute",
            "compliance_warnings",
            "created_at",
            "updated_at",
        ]


class TelehealthEncounterCreateSerializer(serializers.ModelSerializer):
    """Create serializer that auto-fills compliance fields."""

    class Meta:
        model = TelehealthEncounter
        fields = [
            "encounter",
            "patient_location_state",
            "patient_location_city",
            "patient_location_setting",
            "provider_location_state",
            "provider_location_city",
            "modality",
            "platform",
            "consent_obtained",
            "consent_timestamp",
            "technology_adequate",
            "technology_notes",
        ]

    def create(self, validated_data):
        from services.compliance_service import ComplianceService

        service = ComplianceService()

        patient_state = validated_data["patient_location_state"]
        provider_state = validated_data.get("provider_location_state", "")
        patient_setting = validated_data.get("patient_location_setting", "home")
        modality = validated_data.get("modality", "audio_video")

        report = service.generate_compliance_report(
            patient_state=patient_state,
            provider_state=provider_state,
            patient_setting=patient_setting,
            modality=modality,
        )

        validated_data["pos_code"] = report["pos_code"]
        validated_data["cpt_modifier"] = report["cpt_modifier"]
        validated_data["consent_type"] = report["consent"]["consent_type"]
        validated_data["consent_statute"] = report["consent"].get("consent_statute", "")
        validated_data["compliance_warnings"] = report["warnings"]

        return super().create(validated_data)


class StateComplianceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = StateComplianceRule
        fields = [
            "id",
            "state_code",
            "state_name",
            "consent_type",
            "consent_required",
            "consent_statute",
            "recording_consent",
            "prescribing_restrictions",
            "interstate_compact",
            "medicaid_coverage",
            "additional_rules",
            "effective_date",
            "is_active",
        ]
        read_only_fields = fields


class ComplianceCheckSerializer(serializers.Serializer):
    """Input serializer for checking compliance before creating encounter."""

    patient_state = serializers.CharField(max_length=2)
    provider_state = serializers.CharField(max_length=2)
    patient_setting = serializers.ChoiceField(
        choices=TelehealthEncounter.PatientSetting.choices, default="home"
    )
    modality = serializers.ChoiceField(
        choices=TelehealthEncounter.Modality.choices, default="audio_video"
    )
