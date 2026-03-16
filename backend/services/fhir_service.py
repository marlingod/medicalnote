import logging
from datetime import timedelta

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


class FHIRService:
    """FHIR R4 client for pushing clinical notes to EHR systems."""

    def __init__(self, connection):
        self.connection = connection
        self.base_url = connection.fhir_base_url.rstrip("/")
        self._access_token = None

    def _get_access_token(self) -> str:
        """Obtain or refresh OAuth2 access token."""
        if (
            self.connection.access_token
            and self.connection.token_expires_at
            and self.connection.token_expires_at > timezone.now()
        ):
            return self.connection.access_token

        if self.connection.auth_type == "client_credentials":
            return self._client_credentials_flow()
        elif self.connection.auth_type == "backend_service":
            return self._backend_service_flow()
        else:
            raise ValueError(
                f"Unsupported auth type: {self.connection.auth_type}"
            )

    def _client_credentials_flow(self) -> str:
        token_url = (
            self.connection.smart_token_url
            or f"{self.base_url}/oauth2/token"
        )
        response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.connection.client_id,
                "client_secret": self.connection.client_secret,
                "scope": self.connection.scopes,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise ConnectionError(
                f"Token request failed: {response.status_code} "
                f"{response.text}"
            )

        data = response.json()
        token = data["access_token"]
        expires_in = data.get("expires_in", 3600)

        self.connection.access_token = token
        self.connection.token_expires_at = timezone.now() + timedelta(
            seconds=expires_in
        )
        self.connection.save(
            update_fields=[
                "access_token",
                "token_expires_at",
                "updated_at",
            ]
        )

        return token

    def _backend_service_flow(self) -> str:
        """SMART Backend Service flow (JWT assertion). Placeholder."""
        raise NotImplementedError(
            "Backend service auth not yet implemented"
        )

    def build_document_reference(self, note, encounter) -> dict:
        """Build a FHIR DocumentReference resource from a ClinicalNote."""
        note_text = (
            f"SUBJECTIVE:\n{note.subjective}\n\n"
            f"OBJECTIVE:\n{note.objective}\n\n"
            f"ASSESSMENT:\n{note.assessment}\n\n"
            f"PLAN:\n{note.plan}"
        )

        resource = {
            "resourceType": "DocumentReference",
            "status": "current",
            "type": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "11488-4",
                        "display": "Consultation note",
                    }
                ],
            },
            "subject": {
                "display": f"Patient {encounter.patient_id}",
            },
            "date": encounter.encounter_date.isoformat(),
            "author": [
                {
                    "display": f"Dr. {encounter.doctor.last_name}",
                }
            ],
            "description": f"Clinical note for encounter {encounter.id}",
            "content": [
                {
                    "attachment": {
                        "contentType": "text/plain",
                        "data": note_text,
                        "title": (
                            f"SOAP Note - {encounter.encounter_date}"
                        ),
                    },
                }
            ],
            "context": {
                "encounter": [
                    {
                        "display": f"Encounter {encounter.id}",
                    }
                ],
            },
        }

        if note.icd10_codes:
            resource["context"]["related"] = [
                {"display": f"ICD-10: {code}"}
                for code in note.icd10_codes
            ]

        return resource

    def build_composition(self, note, encounter) -> dict:
        """Build a FHIR Composition resource from a ClinicalNote."""
        return {
            "resourceType": "Composition",
            "status": "final",
            "type": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "11488-4",
                        "display": "Consultation note",
                    }
                ],
            },
            "date": encounter.encounter_date.isoformat(),
            "title": (
                f"Clinical Note - {encounter.encounter_date}"
            ),
            "subject": {
                "display": f"Patient {encounter.patient_id}",
            },
            "author": [
                {
                    "display": f"Dr. {encounter.doctor.last_name}",
                }
            ],
            "section": [
                {
                    "title": "Subjective",
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "61150-9",
                                "display": "Subjective",
                            }
                        ]
                    },
                    "text": {
                        "status": "generated",
                        "div": f"<div>{note.subjective}</div>",
                    },
                },
                {
                    "title": "Objective",
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "61153-3",
                                "display": "Objective",
                            }
                        ]
                    },
                    "text": {
                        "status": "generated",
                        "div": f"<div>{note.objective}</div>",
                    },
                },
                {
                    "title": "Assessment",
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "51848-0",
                                "display": "Assessment",
                            }
                        ]
                    },
                    "text": {
                        "status": "generated",
                        "div": f"<div>{note.assessment}</div>",
                    },
                },
                {
                    "title": "Plan",
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "18776-5",
                                "display": "Plan",
                            }
                        ]
                    },
                    "text": {
                        "status": "generated",
                        "div": f"<div>{note.plan}</div>",
                    },
                },
            ],
        }

    def push_note_to_ehr(self, note, encounter) -> dict:
        """Push a clinical note to the connected EHR as DocumentReference."""
        from apps.fhir.models import FHIRPushLog

        try:
            token = self._get_access_token()
        except Exception as e:
            log = FHIRPushLog.objects.create(
                connection=self.connection,
                encounter=encounter,
                clinical_note=note,
                resource_type="DocumentReference",
                status="failed",
                error_message=f"Auth failed: {e}",
            )
            return {
                "status": "failed",
                "error": str(e),
                "log_id": str(log.id),
            }

        resource = self.build_document_reference(note, encounter)

        try:
            response = requests.post(
                f"{self.base_url}/DocumentReference",
                json=resource,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/fhir+json",
                    "Accept": "application/fhir+json",
                },
                timeout=30,
            )

            if response.status_code in (200, 201):
                response_data = response.json()
                fhir_id = response_data.get("id", "")
                log = FHIRPushLog.objects.create(
                    connection=self.connection,
                    encounter=encounter,
                    clinical_note=note,
                    resource_type="DocumentReference",
                    fhir_resource_id=fhir_id,
                    status="success",
                    response_code=response.status_code,
                    response_body=response_data,
                )
                self.connection.last_connected_at = timezone.now()
                self.connection.connection_status = "connected"
                self.connection.save(
                    update_fields=[
                        "last_connected_at",
                        "connection_status",
                        "updated_at",
                    ]
                )
                return {
                    "status": "success",
                    "fhir_resource_id": fhir_id,
                    "log_id": str(log.id),
                    "response_code": response.status_code,
                }
            else:
                try:
                    resp_body = response.json()
                except Exception:
                    resp_body = {}
                log = FHIRPushLog.objects.create(
                    connection=self.connection,
                    encounter=encounter,
                    clinical_note=note,
                    resource_type="DocumentReference",
                    status="failed",
                    response_code=response.status_code,
                    error_message=response.text[:500],
                    response_body=resp_body,
                )
                return {
                    "status": "failed",
                    "response_code": response.status_code,
                    "error": response.text[:500],
                    "log_id": str(log.id),
                }

        except requests.RequestException as e:
            log = FHIRPushLog.objects.create(
                connection=self.connection,
                encounter=encounter,
                clinical_note=note,
                resource_type="DocumentReference",
                status="failed",
                error_message=str(e),
            )
            return {
                "status": "failed",
                "error": str(e),
                "log_id": str(log.id),
            }
