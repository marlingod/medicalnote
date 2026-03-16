from datetime import date

from django.test import TestCase

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.fhir.models import FHIRConnection, FHIRPushLog
from apps.notes.models import ClinicalNote
from apps.patients.models import Patient


class FHIRConnectionModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="FHIR Clinic", subscription_tier="solo"
        )

    def test_create_connection(self):
        conn = FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="athenahealth",
            display_name="Athena Production",
            fhir_base_url="https://api.athenahealth.com/fhir/r4",
            client_id="test_client_id",
            client_secret="test_secret",
            auth_type="client_credentials",
            scopes="patient/*.read system/*.write",
            is_active=True,
        )
        assert conn.id is not None
        assert conn.ehr_system == "athenahealth"
        assert conn.is_active is True

    def test_connection_str(self):
        conn = FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="eclinicalworks",
            display_name="eCW",
            fhir_base_url="https://fhir.eclinicalworks.com/r4",
        )
        assert "eCW" in str(conn)

    def test_connection_defaults(self):
        conn = FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="epic",
            display_name="Epic",
            fhir_base_url="https://fhir.epic.com/r4",
        )
        assert conn.is_active is False
        assert conn.connection_status == "disconnected"
        assert conn.auth_type == "client_credentials"


class FHIRPushLogModelTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Push Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="push_doc@test.com",
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
        )
        self.connection = FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="athenahealth",
            display_name="Athena",
            fhir_base_url="https://api.athenahealth.com/fhir/r4",
            is_active=True,
        )

    def test_create_push_log(self):
        log = FHIRPushLog.objects.create(
            connection=self.connection,
            encounter=self.encounter,
            clinical_note=self.note,
            resource_type="DocumentReference",
            fhir_resource_id="doc-ref-123",
            status="success",
            response_code=201,
            response_body={
                "id": "doc-ref-123",
                "resourceType": "DocumentReference",
            },
        )
        assert log.id is not None
        assert log.status == "success"
        assert log.response_code == 201

    def test_push_log_failure(self):
        log = FHIRPushLog.objects.create(
            connection=self.connection,
            encounter=self.encounter,
            clinical_note=self.note,
            resource_type="DocumentReference",
            status="failed",
            response_code=401,
            error_message="Authentication failed",
        )
        assert log.status == "failed"
        assert log.error_message == "Authentication failed"

    def test_push_log_str(self):
        log = FHIRPushLog.objects.create(
            connection=self.connection,
            encounter=self.encounter,
            clinical_note=self.note,
            resource_type="DocumentReference",
            status="success",
        )
        assert "DocumentReference" in str(log)
        assert "success" in str(log)
