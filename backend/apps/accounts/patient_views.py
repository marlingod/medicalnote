from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.models import DeviceToken
from apps.accounts.permissions import IsPatient
from apps.accounts.serializers import DeviceTokenSerializer, PatientProfileSerializer


@api_view(["POST"])
@permission_classes([IsPatient])
def register_device_token(request):
    token_value = request.data.get("token")
    existing = None
    if token_value:
        existing = DeviceToken.objects.filter(user=request.user, token=token_value).first()

    if existing:
        serializer = DeviceTokenSerializer(existing, data=request.data, partial=True)
    else:
        serializer = DeviceTokenSerializer(data=request.data)

    serializer.is_valid(raise_exception=True)
    token_val = serializer.validated_data["token"]
    platform = serializer.validated_data["platform"]

    device_token, created = DeviceToken.objects.update_or_create(
        user=request.user,
        token=token_val,
        defaults={"platform": platform, "is_active": True},
    )
    output_serializer = DeviceTokenSerializer(device_token)
    return Response(
        output_serializer.data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsPatient])
def patient_profile(request):
    if request.method == "GET":
        serializer = PatientProfileSerializer(request.user)
        return Response(serializer.data)

    serializer = PatientProfileSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)
