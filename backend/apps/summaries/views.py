import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.models import DeviceToken, User
from apps.accounts.permissions import IsDoctorOrAdmin
from apps.encounters.models import Encounter
from apps.summaries.models import PatientSummary
from apps.summaries.serializers import PatientSummarySerializer
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def _send_push_to_patient(patient, summary):
    """Look up patient's device token and send a push notification for a new summary."""
    # Find user accounts matching the patient's phone
    if not patient.phone:
        return

    # Iterate over patient users to find matching phone (encrypted fields)
    patient_users = User.objects.filter(role="patient")
    matching_user = None
    for user in patient_users.iterator():
        if user.phone and user.phone == patient.phone:
            matching_user = user
            break

    if not matching_user:
        return

    device_tokens = DeviceToken.objects.filter(user=matching_user, is_active=True)
    if not device_tokens.exists():
        return

    service = NotificationService()
    for dt in device_tokens:
        try:
            service.send_push_notification(
                device_token=dt.token,
                title="New Visit Summary",
                body="Your doctor has sent you a new visit summary.",
                data={"summary_id": str(summary.id)},
            )
        except Exception:
            logger.error(f"Failed to send push to device {dt.id}", exc_info=True)


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
        encounter = Encounter.objects.select_related("patient").get(
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

    # Send push notification to patient
    _send_push_to_patient(encounter.patient, summary)

    return Response(PatientSummarySerializer(summary).data)
