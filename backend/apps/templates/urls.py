from rest_framework.routers import DefaultRouter
from apps.templates.views import NoteTemplateViewSet

router = DefaultRouter()
router.register("", NoteTemplateViewSet, basename="template")

urlpatterns = router.urls
