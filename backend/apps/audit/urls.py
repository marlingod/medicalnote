from django.urls import path

from apps.audit.views import BreakGlassRequestView

urlpatterns = [
    path("break-glass/", BreakGlassRequestView.as_view(), name="break-glass-request"),
]
