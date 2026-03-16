from django.urls import path

from apps.accounts.practice_views import (
    PracticeDetailView,
    PracticeAuditLogView,
    PracticeStatsView,
)

urlpatterns = [
    path("", PracticeDetailView.as_view(), name="practice-detail"),
    path("stats/", PracticeStatsView.as_view(), name="practice-stats"),
    path("audit-log/", PracticeAuditLogView.as_view(), name="practice-audit-log"),
]
