from rest_framework import viewsets

from apps.accounts.permissions import IsDoctorOrAdmin, IsSamePractice
from apps.patients.filters import PatientFilter
from apps.patients.models import Patient
from apps.patients.serializers import PatientListSerializer, PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [IsDoctorOrAdmin]
    filterset_class = PatientFilter

    def get_queryset(self):
        return Patient.objects.filter(practice=self.request.user.practice)

    def get_serializer_class(self):
        if self.action == "list":
            return PatientListSerializer
        return PatientSerializer
