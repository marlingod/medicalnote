from rest_framework import serializers

from apps.encounters.models import Encounter, Recording, Transcript


class TranscriptSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

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
    id = serializers.CharField(read_only=True)
    doctor = serializers.CharField(source="doctor.id", read_only=True)
    patient = serializers.PrimaryKeyRelatedField(
        queryset=Encounter._meta.get_field("patient").related_model.objects.all(),
    )

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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Ensure patient and template_used are serialized as strings
        if ret.get("patient") is not None:
            ret["patient"] = str(ret["patient"])
        if ret.get("template_used") is not None:
            ret["template_used"] = str(ret["template_used"])
        return ret

    def create(self, validated_data):
        validated_data["doctor"] = self.context["request"].user
        return super().create(validated_data)


class EncounterDetailSerializer(EncounterSerializer):
    """Detail serializer with nested outputs."""

    has_recording = serializers.SerializerMethodField()
    has_transcript = serializers.SerializerMethodField()
    has_note = serializers.SerializerMethodField()
    has_summary = serializers.SerializerMethodField()
    has_telehealth = serializers.SerializerMethodField()
    has_quality_score = serializers.SerializerMethodField()

    class Meta(EncounterSerializer.Meta):
        fields = EncounterSerializer.Meta.fields + [
            "has_recording",
            "has_transcript",
            "has_note",
            "has_summary",
            "has_telehealth",
            "has_quality_score",
        ]

    def get_has_recording(self, obj):
        return hasattr(obj, "recording")

    def get_has_transcript(self, obj):
        return hasattr(obj, "transcript")

    def get_has_note(self, obj):
        return hasattr(obj, "clinical_note")

    def get_has_summary(self, obj):
        return hasattr(obj, "patient_summary")

    def get_has_telehealth(self, obj):
        return hasattr(obj, "telehealth")

    def get_has_quality_score(self, obj):
        return hasattr(obj, "quality_score")


class PasteInputSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=10, max_length=50000)


class DictationInputSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=10, max_length=50000)


class VoiceTranscriptSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=10, max_length=100000)
    device_model = serializers.CharField(max_length=100, required=False, default="")
    whisper_model = serializers.CharField(max_length=50, required=False, default="base")
    confidence = serializers.FloatField(required=False, default=0.0)
    language = serializers.CharField(max_length=10, required=False, default="en")
