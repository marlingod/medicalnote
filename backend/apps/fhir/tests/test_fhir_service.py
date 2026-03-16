from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter
from apps.fhir.models import FHIRConnection
from apps.notes.models import ClinicalNote
from apps.patients.models import Patient
from services.fhir_service import FHIRService


class FHIRServiceTest(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            name="FHIR Clinic", subscription_tier="solo"
        )
        self.doctor = User.objects.create_user(
            email="fhir_doc@test.com",
            password="test",
            role="doctor",
            practice=self.practice,
            first_name="FHIR",
            last_name="Doc",
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="F",
            last_name="P",
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
            subjective="Headache",
            objective="Alert",
            assessment="Tension HA",
            plan="Ibuprofen",
            ai_generated=True,
            icd10_codes=["R51.9"],
            cpt_codes=["99213"],
            approved_at=timezone.now(),
            approved_by=self.doctor,
        )
        self.connection = FHIRConnection.objects.create(
            practice=self.practice,
            ehr_system="athenahealth",
            display_name="Athena Test",
            fhir_base_url="https://api.athena.test/fhir/r4",
            client_id="test_id",
            client_secret="test_secret",
            auth_type="client_credentials",
            is_active=True,
        )
        self.service = FHIRService(self.connection)

    def test_build_document_reference(self):
        resource = self.service.build_document_reference(
            self.note, self.encounter
        )
        assert resource["resourceType"] == "DocumentReference"
        assert resource["status"] == "current"
        assert (
            resource["type"]["coding"][0]["system"] == "http://loinc.org"
        )
        assert len(resource["content"]) > 0

    def test_build_composition(self):
        resource = self.service.build_composition(
            self.note, self.encounter
        )
        assert resource["resourceType"] == "Composition"
        assert resource["status"] == "final"
        assert len(resource["section"]) == 4  # S, O, A, P

    def test_build_document_reference_includes_icd_codes(self):
        resource = self.service.build_document_reference(
            self.note, self.encounter
        )
        related = resource.get("context", {}).get("related", [])
        assert len(related) > 0
        assert any("R51.9" in r["display"] for r in related)

    @patch("services.fhir_service.requests")
    def test_push_document_reference_success(self, mock_requests):
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }

        mock_push_response = MagicMock()
        mock_push_response.status_code = 201
        mock_push_response.json.return_value = {
            "id": "doc-ref-abc",
            "resourceType": "DocumentReference",
        }

        mock_requests.post.side_effect = [
            mock_token_response,
            mock_push_response,
        ]

        result = self.service.push_note_to_ehr(self.note, self.encounter)
        assert result["status"] == "success"
        assert result["fhir_resource_id"] == "doc-ref-abc"

    @patch("services.fhir_service.requests")
    def test_push_document_reference_failure(self, mock_requests):
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }

        mock_push_response = MagicMock()
        mock_push_response.status_code = 401
        mock_push_response.text = "Unauthorized"
        mock_push_response.headers = {
            "content-type": "application/json",
        }
        mock_push_response.json.return_value = {
            "error": "invalid_token",
        }

        mock_requests.post.side_effect = [
            mock_token_response,
            mock_push_response,
        ]

        result = self.service.push_note_to_ehr(self.note, self.encounter)
        assert result["status"] == "failed"
        assert result["response_code"] == 401

    @patch("services.fhir_service.requests")
    def test_push_auth_failure(self, mock_requests):
        mock_token_response = MagicMock()
        mock_token_response.status_code = 401
        mock_token_response.text = "Invalid credentials"

        mock_requests.post.return_value = mock_token_response

        result = self.service.push_note_to_ehr(self.note, self.encounter)
        assert result["status"] == "failed"
        assert "Auth failed" in result["error"]
