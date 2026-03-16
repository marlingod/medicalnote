from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsDoctorOrAdmin, IsPatient
from apps.encounters.models import Encounter
from apps.summaries.models import PatientSummary
from apps.summaries.serializers import PatientSummarySerializer


@api_view(["GET"])
@permission_classes([IsDoctorOrAdmin])
def encounter_summary(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id, doctor__practice=request.user.practice
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    try:
        summary = encounter.patient_summary
    except PatientSummary.DoesNotExist:
        return Response({"error": "No summary available."}, status=status.HTTP_404_NOT_FOUND)
    return Response(PatientSummarySerializer(summary).data)


@api_view(["POST"])
@permission_classes([IsDoctorOrAdmin])
def send_summary(request, encounter_id):
    try:
        encounter = Encounter.objects.get(
            id=encounter_id, doctor__practice=request.user.practice
        )
    except Encounter.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    try:
        summary = encounter.patient_summary
    except PatientSummary.DoesNotExist:
        return Response({"error": "No summary available."}, status=status.HTTP_404_NOT_FOUND)

    delivery_method = request.data.get("delivery_method", "app")
    summary.delivery_status = "sent"
    summary.delivered_at = timezone.now()
    summary.delivery_method = delivery_method
    summary.save(update_fields=["delivery_status", "delivered_at", "delivery_method", "updated_at"])

    encounter.status = Encounter.Status.DELIVERED
    encounter.save(update_fields=["status", "updated_at"])

    return Response(PatientSummarySerializer(summary).data)
