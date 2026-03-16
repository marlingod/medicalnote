from django.urls import path
from apps.summaries.views import encounter_summary, send_summary

urlpatterns = [
    # These are mounted under /api/v1/encounters/ via encounter urls
]

# Standalone encounter-scoped summary endpoints added to encounters/urls.py
