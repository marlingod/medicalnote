from django.urls import include, path

from apps.accounts.views import patient_otp_send, patient_otp_verify

urlpatterns = [
    # dj-rest-auth endpoints (login, logout, user, password)
    path("", include("dj_rest_auth.urls")),
    # dj-rest-auth registration
    path("registration/", include("dj_rest_auth.registration.urls")),
    # Custom patient OTP endpoints
    path("patient/otp/send/", patient_otp_send, name="patient-otp-send"),
    path("patient/otp/verify/", patient_otp_verify, name="patient-otp-verify"),
]
