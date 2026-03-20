from rest_framework import serializers
from .models import BusinessAssociateAgreement, BreachIncident


class BAASerializer(serializers.ModelSerializer):
    is_expiring_soon = serializers.ReadOnlyField()

    class Meta:
        model = BusinessAssociateAgreement
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class BreachIncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BreachIncident
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "notification_deadline"]
