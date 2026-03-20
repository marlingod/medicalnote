from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.patients.views import PatientViewSet
from apps.patients.export_views import PatientDataExportView

router = DefaultRouter()
router.register("", PatientViewSet, basename="patient")

urlpatterns = [
    path("export/", PatientDataExportView.as_view(), name="patient-data-export"),
] + router.urls
