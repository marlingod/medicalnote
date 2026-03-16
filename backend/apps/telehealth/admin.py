from django.contrib import admin

from apps.telehealth.models import StateComplianceRule, TelehealthEncounter


@admin.register(TelehealthEncounter)
class TelehealthEncounterAdmin(admin.ModelAdmin):
    list_display = [
        "encounter",
        "modality",
        "patient_location_state",
        "provider_location_state",
        "pos_code",
        "cpt_modifier",
        "consent_obtained",
        "created_at",
    ]
    list_filter = ["modality", "patient_location_state", "pos_code"]
    readonly_fields = [
        "pos_code",
        "cpt_modifier",
        "consent_statute",
        "compliance_warnings",
    ]


@admin.register(StateComplianceRule)
class StateComplianceRuleAdmin(admin.ModelAdmin):
    list_display = [
        "state_code",
        "state_name",
        "consent_type",
        "consent_required",
        "recording_consent",
        "interstate_compact",
        "medicaid_coverage",
        "is_active",
    ]
    list_filter = [
        "consent_type",
        "recording_consent",
        "interstate_compact",
        "is_active",
    ]
    search_fields = ["state_code", "state_name"]
