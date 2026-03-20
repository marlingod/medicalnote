from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import BusinessAssociateAgreement, BreachIncident
from .serializers import BAASerializer, BreachIncidentSerializer


class AdminOnlyMixin:
    def check_permissions(self, request):
        super().check_permissions(request)
        if not hasattr(request.user, "role") or request.user.role != "admin":
            self.permission_denied(request, message="Admin access required.")


class BAAViewSet(AdminOnlyMixin, viewsets.ModelViewSet):
    queryset = BusinessAssociateAgreement.objects.all()
    serializer_class = BAASerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def expiring(self, request):
        baas = self.queryset.filter(status="active")
        expiring = [baa for baa in baas if baa.is_expiring_soon]
        serializer = self.get_serializer(expiring, many=True)
        return Response(serializer.data)


class BreachIncidentViewSet(AdminOnlyMixin, viewsets.ModelViewSet):
    queryset = BreachIncident.objects.all()
    serializer_class = BreachIncidentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def notify(self, request, pk=None):
        incident = self.get_object()
        from django.utils import timezone
        incident.status = BreachIncident.Status.NOTIFIED
        incident.hhs_notified_at = timezone.now()
        incident.save()
        return Response(BreachIncidentSerializer(incident).data)
