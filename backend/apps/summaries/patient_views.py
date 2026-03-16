from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsPatient
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary
from apps.summaries.serializers import PatientFacingSummarySerializer


def _get_patient_ids_for_user(user):
    """Get patient record IDs that match the authenticated user's phone.

    Since phone is stored encrypted, we can't use ORM filtering.
    Instead we iterate over patients and compare decrypted values.
    """
    if not user.phone:
        return []
    # In production with many patients, consider a phone_hash blind index
    patient_ids = []
    for patient in Patient.objects.all().iterator():
        if patient.phone and patient.phone == user.phone:
            patient_ids.append(patient.id)
    return patient_ids


@api_view(["GET"])
@permission_classes([IsPatient])
def patient_summary_list(request):
    patient_ids = _get_patient_ids_for_user(request.user)
    summaries = PatientSummary.objects.filter(
        encounter__patient_id__in=patient_ids,
        delivery_status__in=["sent", "viewed"],
    ).select_related("encounter", "encounter__doctor").order_by("-created_at")
    serializer = PatientFacingSummarySerializer(summaries, many=True)
    return Response({"count": summaries.count(), "results": serializer.data})


@api_view(["GET"])
@permission_classes([IsPatient])
def patient_summary_detail(request, summary_id):
    patient_ids = _get_patient_ids_for_user(request.user)
    try:
        summary = PatientSummary.objects.select_related(
            "encounter", "encounter__doctor"
        ).get(id=summary_id, encounter__patient_id__in=patient_ids)
    except PatientSummary.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(PatientFacingSummarySerializer(summary).data)


@api_view(["PATCH"])
@permission_classes([IsPatient])
def patient_summary_mark_read(request, summary_id):
    patient_ids = _get_patient_ids_for_user(request.user)
    try:
        summary = PatientSummary.objects.get(
            id=summary_id, encounter__patient_id__in=patient_ids
        )
    except PatientSummary.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    summary.delivery_status = "viewed"
    summary.viewed_at = timezone.now()
    summary.save(update_fields=["delivery_status", "viewed_at", "updated_at"])
    return Response({"status": "viewed"})
