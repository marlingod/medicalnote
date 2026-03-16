from rest_framework.routers import DefaultRouter

from apps.fhir.views import FHIRConnectionViewSet

router = DefaultRouter()
router.register("connections", FHIRConnectionViewSet, basename="fhir-connection")

urlpatterns = router.urls
