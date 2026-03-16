from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Practice
from apps.accounts.permissions import IsDoctorOrAdmin, IsAdmin
from apps.accounts.serializers import PracticeSerializer
from apps.audit.models import AuditLog


class PracticeDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PracticeSerializer
    permission_classes = [IsDoctorOrAdmin]

    def get_object(self):
        return self.request.user.practice


class PracticeStatsView(APIView):
    permission_classes = [IsDoctorOrAdmin]

    def get(self, request):
        from apps.encounters.models import Encounter
        from apps.patients.models import Patient

        practice = request.user.practice
        stats = {
            "total_patients": Patient.objects.filter(practice=practice).count(),
            "total_encounters": Encounter.objects.filter(
                doctor__practice=practice
            ).count(),
            "encounters_by_status": {},
        }
        for status_choice in Encounter.Status.values:
            count = Encounter.objects.filter(
                doctor__practice=practice, status=status_choice
            ).count()
            if count > 0:
                stats["encounters_by_status"][status_choice] = count
        return Response(stats)


class PracticeAuditLogView(generics.ListAPIView):
    permission_classes = [IsAdmin]

    def get_queryset(self):
        practice = self.request.user.practice
        return AuditLog.objects.filter(user__practice=practice)

    class AuditLogSerializer:
        pass  # Placeholder - implemented in Task 3.1 Step 6

    def get_serializer_class(self):
        from rest_framework import serializers

        class AuditLogListSerializer(serializers.ModelSerializer):
            user_email = serializers.CharField(source="user.email", read_only=True)

            class Meta:
                model = AuditLog
                fields = [
                    "id",
                    "user_email",
                    "action",
                    "resource_type",
                    "resource_id",
                    "ip_address",
                    "phi_accessed",
                    "created_at",
                ]

        return AuditLogListSerializer
