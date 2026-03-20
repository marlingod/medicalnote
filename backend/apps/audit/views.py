import uuid
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog, BreakGlassAccess


class BreakGlassRequestSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    reason = serializers.CharField(min_length=10, max_length=1000)


class BreakGlassRequestView(APIView):
    """Emergency access to patient records outside normal RBAC (HIPAA §164.312(a)(2)(ii))."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BreakGlassRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        patient_id = serializer.validated_data["patient_id"]
        reason = serializer.validated_data["reason"]

        # Create break-glass access record
        access = BreakGlassAccess.objects.create(
            user=request.user,
            patient_id=patient_id,
            reason=reason,
            expires_at=timezone.now() + timedelta(hours=4),
        )

        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.BREAK_GLASS,
            resource_type=AuditLog.ResourceType.PATIENT,
            resource_id=patient_id,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            phi_accessed=True,
            outcome=AuditLog.Outcome.SUCCESS,
            user_role=getattr(request.user, "role", ""),
            details={"reason": reason, "break_glass_id": str(access.id)},
        )

        return Response(
            {
                "id": str(access.id),
                "expires_at": access.expires_at.isoformat(),
                "message": "Emergency access granted. This action has been logged and admins notified.",
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
