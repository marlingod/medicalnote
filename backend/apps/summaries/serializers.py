from rest_framework import serializers
from apps.summaries.models import PatientSummary


class PatientSummarySerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    encounter = serializers.CharField(source="encounter.id", read_only=True)
    clinical_note = serializers.CharField(source="clinical_note.id", read_only=True)
    prompt_version = serializers.CharField(source="prompt_version.id", read_only=True, default=None)

    class Meta:
        model = PatientSummary
        fields = [
            "id", "encounter", "clinical_note", "summary_en", "summary_es",
            "reading_level", "medical_terms_explained", "disclaimer_text",
            "delivery_status", "delivered_at", "viewed_at", "delivery_method",
            "prompt_version", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "encounter", "clinical_note", "summary_en", "summary_es",
            "reading_level", "medical_terms_explained", "disclaimer_text",
            "prompt_version", "created_at", "updated_at",
        ]


class PatientFacingSummarySerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    doctor_name = serializers.SerializerMethodField()
    encounter_date = serializers.DateField(source="encounter.encounter_date", read_only=True)

    class Meta:
        model = PatientSummary
        fields = [
            "id", "summary_en", "summary_es", "reading_level",
            "medical_terms_explained", "disclaimer_text",
            "encounter_date", "doctor_name", "delivery_status",
            "viewed_at", "created_at",
        ]

    def get_doctor_name(self, obj):
        doctor = obj.encounter.doctor
        return f"Dr. {doctor.last_name}" if doctor.last_name else doctor.email
