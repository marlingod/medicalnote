from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/patients/", include("apps.patients.urls")),
    path("api/v1/encounters/", include("apps.encounters.urls")),
    path("api/v1/notes/", include("apps.notes.urls")),
    path("api/v1/summaries/", include("apps.summaries.urls")),
    path("api/v1/widget/", include("apps.widget.urls")),
    path("api/v1/practice/", include("apps.accounts.practice_urls")),
    path("api/v1/patient/", include("apps.summaries.patient_urls")),
]
