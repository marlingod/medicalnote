from rest_framework import serializers

from apps.encounters.models import Encounter, Recording, Transcript


class TranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcript
        fields = [
            "id",
            "raw_text",
            "speaker_segments",
            "medical_terms_detected",
            "confidence_score",
            "language_detected",
            "created_at",
        ]
        read_only_fields = fields


class RecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recording
        fields = [
            "id",
            "storage_url",
            "duration_seconds",
            "file_size_bytes",
            "format",
            "transcription_status",
            "created_at",
        ]
        read_only_fields = fields


class EncounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Encounter
        fields = [
            "id",
            "doctor",
            "patient",
            "encounter_date",
            "input_method",
            "status",
            "consent_recording",
            "consent_timestamp",
            "consent_method",
            "consent_jurisdiction_state",
            "template_used",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "doctor", "status", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["doctor"] = self.context["request"].user
        return super().create(validated_data)


class EncounterDetailSerializer(EncounterSerializer):
    """Detail serializer with nested outputs."""

    has_recording = serializers.SerializerMethodField()
    has_transcript = serializers.SerializerMethodField()
    has_note = serializers.SerializerMethodField()
    has_summary = serializers.SerializerMethodField()

    class Meta(EncounterSerializer.Meta):
        fields = EncounterSerializer.Meta.fields + [
            "has_recording",
            "has_transcript",
            "has_note",
            "has_summary",
        ]

    def get_has_recording(self, obj):
        return hasattr(obj, "recording")

    def get_has_transcript(self, obj):
        return hasattr(obj, "transcript")

    def get_has_note(self, obj):
        return hasattr(obj, "clinical_note")

    def get_has_summary(self, obj):
        return hasattr(obj, "patient_summary")


class PasteInputSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=10, max_length=50000)


class DictationInputSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=10, max_length=50000)
