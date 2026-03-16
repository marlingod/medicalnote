from rest_framework import serializers

from apps.fhir.models import FHIRConnection, FHIRPushLog


class FHIRConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FHIRConnection
        fields = [
            "id",
            "ehr_system",
            "display_name",
            "fhir_base_url",
            "auth_type",
            "scopes",
            "smart_authorize_url",
            "smart_token_url",
            "is_active",
            "last_connected_at",
            "connection_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "last_connected_at",
            "connection_status",
            "created_at",
            "updated_at",
        ]


class FHIRConnectionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FHIRConnection
        fields = [
            "ehr_system",
            "display_name",
            "fhir_base_url",
            "client_id",
            "client_secret",
            "auth_type",
            "scopes",
            "smart_authorize_url",
            "smart_token_url",
        ]

    def create(self, validated_data):
        validated_data["practice"] = self.context["request"].user.practice
        return super().create(validated_data)


class FHIRPushLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FHIRPushLog
        fields = [
            "id",
            "connection",
            "encounter",
            "clinical_note",
            "resource_type",
            "fhir_resource_id",
            "status",
            "response_code",
            "error_message",
            "retry_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
