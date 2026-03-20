from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import BAAViewSet, BreachIncidentViewSet
from .disclosure_views import AccountingOfDisclosuresView

router = DefaultRouter()
router.register(r"baa", BAAViewSet)
router.register(r"breaches", BreachIncidentViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("disclosures/", AccountingOfDisclosuresView.as_view(), name="accounting-of-disclosures"),
]
