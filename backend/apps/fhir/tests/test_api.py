from datetime import date

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.fhir.models import FHIRConnection, FHIRPushLog
from apps.notes.models import ClinicalNote
from apps.patients.models import Patient


class FHIRConnectionAPITest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="FHIR API Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="fhir_api@test.com",
            password="test",
            role="doctor",
            practice=self.practice,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor)

    def test_create_connection(self):
        resp = self.client.post(
            "/api/v1/fhir/connections/",
            {
                "ehr_system": "athenahealth",
                "display_name": "Test Athena",
                "fhir_base_url": "https://api.athena.test/fhir/r4",
                "client_id": "test_id",
                "client_secret": "test_secret",
                "auth_type": "client_credentials",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["ehr_system"], "athenahealth")

    def test_list_connections(self):
        FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="athenahealth",
            display_name="Athena",
            fhir_base_url="https://api.athena.test/fhir/r4",
        )
        resp = self.client.get("/api/v1/fhir/connections/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 1)

    def test_activate_connection(self):
        conn = FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="athenahealth",
            display_name="Athena",
            fhir_base_url="https://api.athena.test/fhir/r4",
        )
        resp = self.client.post(
            f"/api/v1/fhir/connections/{conn.id}/activate/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["is_active"])

    def test_deactivate_connection(self):
        conn = FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="athenahealth",
            display_name="Athena",
            fhir_base_url="https://api.athena.test/fhir/r4",
            is_active=True,
        )
        resp = self.client.post(
            f"/api/v1/fhir/connections/{conn.id}/deactivate/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["is_active"])


class FHIRPushAPITest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Push API Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="push_api@test.com",
            password="test",
            role="doctor",
            practice=self.practice,
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="P",
            last_name="L",
            date_of_birth="1990-01-01",
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            encounter_date=date.today(),
            input_method="paste",
            status="approved",
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="S",
            objective="O",
            assessment="A",
            plan="P",
            ai_generated=True,
            approved_at=timezone.now(),
            approved_by=self.doctor,
        )
        self.connection = FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="athenahealth",
            display_name="Athena",
            fhir_base_url="https://api.athena.test/fhir/r4",
            is_active=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor)

    def test_push_requires_approved_note(self):
        self.note.approved_at = None
        self.note.save()
        resp = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/fhir/push/"
        )
        self.assertEqual(resp.status_code, 400)

    def test_push_requires_active_connection(self):
        self.connection.is_active = False
        self.connection.save()
        resp = self.client.post(
            f"/api/v1/encounters/{self.encounter.id}/fhir/push/"
        )
        self.assertEqual(resp.status_code, 400)

    def test_get_push_logs(self):
        FHIRPushLog.objects.create(
            connection=self.connection,
            encounter=self.encounter,
            clinical_note=self.note,
            resource_type="DocumentReference",
            status="success",
            response_code=201,
        )
        resp = self.client.get(
            f"/api/v1/encounters/{self.encounter.id}/fhir/logs/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_push_logs_empty(self):
        resp = self.client.get(
            f"/api/v1/encounters/{self.encounter.id}/fhir/logs/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)
