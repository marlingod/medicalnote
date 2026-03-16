from rest_framework import serializers

from apps.notes.models import ClinicalNote, PromptVersion


class PromptVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptVersion
        fields = ["id", "prompt_name", "version", "is_active", "created_at"]
        read_only_fields = fields


class ClinicalNoteSerializer(serializers.ModelSerializer):
    prompt_version_detail = PromptVersionSerializer(source="prompt_version", read_only=True)

    class Meta:
        model = ClinicalNote
        fields = [
            "id",
            "encounter",
            "note_type",
            "subjective",
            "objective",
            "assessment",
            "plan",
            "raw_content",
            "icd10_codes",
            "cpt_codes",
            "ai_generated",
            "doctor_edited",
            "approved_at",
            "approved_by",
            "prompt_version",
            "prompt_version_detail",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "encounter",
            "ai_generated",
            "approved_at",
            "approved_by",
            "prompt_version",
            "created_at",
            "updated_at",
        ]
