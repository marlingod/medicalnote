from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.models import Practice
from apps.summaries.models import PatientSummary
from apps.summaries.serializers import PatientFacingSummarySerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def widget_config(request, widget_key):
    try:
        practice = Practice.objects.get(white_label_config__widget_key=widget_key)
    except Practice.DoesNotExist:
        return Response({"error": "Invalid widget key."}, status=status.HTTP_404_NOT_FOUND)
    config = practice.white_label_config or {}
    config["practice_name"] = practice.name
    return Response(config)


@api_view(["GET"])
@permission_classes([AllowAny])
def widget_summary(request, token):
    signer = TimestampSigner()
    try:
        summary_id = signer.unsign(token, max_age=86400)  # 24h expiry
    except (BadSignature, SignatureExpired):
        return Response({"error": "Invalid or expired token."}, status=status.HTTP_403_FORBIDDEN)
    try:
        summary = PatientSummary.objects.select_related(
            "encounter", "encounter__doctor"
        ).get(id=summary_id)
    except PatientSummary.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(PatientFacingSummarySerializer(summary).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def widget_summary_read(request, token):
    signer = TimestampSigner()
    try:
        summary_id = signer.unsign(token, max_age=86400)
    except (BadSignature, SignatureExpired):
        return Response({"error": "Invalid or expired token."}, status=status.HTTP_403_FORBIDDEN)
    from django.utils import timezone
    PatientSummary.objects.filter(id=summary_id).update(
        delivery_status="viewed", viewed_at=timezone.now()
    )
    return Response({"status": "viewed"})
