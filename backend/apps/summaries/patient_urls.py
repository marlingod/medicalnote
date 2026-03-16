from django.urls import path
from apps.summaries.patient_views import (
    patient_summary_list, patient_summary_detail, patient_summary_mark_read,
)

urlpatterns = [
    path("summaries/", patient_summary_list, name="patient-summaries"),
    path("summaries/<uuid:summary_id>/", patient_summary_detail, name="patient-summary-detail"),
    path("summaries/<uuid:summary_id>/read/", patient_summary_mark_read, name="patient-summary-read"),
]
