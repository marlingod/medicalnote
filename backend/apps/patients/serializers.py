from rest_framework import serializers

from apps.patients.models import Patient


class PatientSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
            "language_preference",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["practice"] = request.user.practice
        return super().create(validated_data)


class PatientListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list view (no full PHI)."""
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "first_name",
            "last_name",
            "language_preference",
            "created_at",
        ]
