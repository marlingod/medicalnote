from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog


class AccountingOfDisclosuresView(APIView):
    """Accounting of disclosures -- HIPAA 164.528."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        patient_id = request.query_params.get("patient_id")
        if not patient_id:
            return Response({"error": "patient_id is required"}, status=400)

        qs = AuditLog.objects.filter(
            action=AuditLog.Action.DISCLOSE,
            resource_id=patient_id,
        )

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            qs = qs.filter(created_at__date__gte=parse_date(start_date))
        if end_date:
            qs = qs.filter(created_at__date__lte=parse_date(end_date))

        disclosures = [
            {
                "id": str(log.id),
                "date": log.created_at.isoformat(),
                "action": log.action,
                "resource_type": log.resource_type,
                "user": str(log.user_id) if log.user_id else None,
                "details": log.details,
            }
            for log in qs[:100]
        ]

        return Response({"patient_id": patient_id, "disclosures": disclosures})
