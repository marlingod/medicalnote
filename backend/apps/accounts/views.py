from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.adapters import PatientOTPAdapter, RateLimitExceeded


class AuthEndpointThrottle(AnonRateThrottle):
    rate = "10/min"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthEndpointThrottle])
def patient_otp_send(request):
    phone = request.data.get("phone")
    if not phone:
        return Response(
            {"error": "Phone number is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    adapter = PatientOTPAdapter()
    try:
        adapter.send_otp(phone)
    except RateLimitExceeded as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except Exception:
        return Response(
            {"error": "Could not send verification code."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return Response(
        {"message": "Verification code sent."},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthEndpointThrottle])
def patient_otp_verify(request):
    phone = request.data.get("phone")
    code = request.data.get("code")
    if not phone or not code:
        return Response(
            {"error": "Phone and code are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    adapter = PatientOTPAdapter()
    try:
        user = adapter.verify_otp(phone, code)
    except RateLimitExceeded as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    if user is None:
        return Response(
            {"error": "Invalid verification code."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user_id": str(user.id),
        },
        status=status.HTTP_200_OK,
    )
