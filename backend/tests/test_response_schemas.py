"""
Response Schema Validation Tests
=================================
Define JSON schemas for each endpoint response and validate against them.
This ensures that if a backend serializer changes, the tests catch breaking
changes before they reach the frontend.

Schemas are derived from the TypeScript interfaces in:
  - web/src/types/index.ts
  - mobile/types/api.ts
  - widget/src/types.ts

Uses a lightweight built-in schema validator (no external jsonschema dependency).
"""

from datetime import date
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.core.signing import TimestampSigner
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.encounters.models import Encounter, Transcript
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


# ---------------------------------------------------------------------------
# Lightweight schema validator (no external dependency)
# ---------------------------------------------------------------------------

_PYTHON_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _check_type(value, type_spec):
    """Return True if *value* matches *type_spec* (a string or list of strings)."""
    if isinstance(type_spec, list):
        # e.g. ["string", "null"]
        for t in type_spec:
            if t == "null" and value is None:
                return True
            if t in _PYTHON_TYPE_MAP and isinstance(value, _PYTHON_TYPE_MAP[t]):
                return True
        return False
    if type_spec == "null":
        return value is None
    return isinstance(value, _PYTHON_TYPE_MAP.get(type_spec, type(None)))


def validate_schema(test_case, data, schema, msg="", path=""):
    """
    Validate *data* against a JSON-Schema-like dict.

    Supports: type, required, properties, additionalProperties, enum,
    items, oneOf, minLength.  Enough for the schemas defined in this file.
    """
    prefix = f"[{msg}] " if msg else ""

    # --- type check ---
    schema_type = schema.get("type")
    if schema_type:
        if not _check_type(data, schema_type):
            test_case.fail(
                f"{prefix}Type mismatch at '{path}': "
                f"expected {schema_type}, got {type(data).__name__} (value={data!r})"
            )

    # --- oneOf ---
    if "oneOf" in schema:
        matched = False
        for sub_schema in schema["oneOf"]:
            try:
                validate_schema(test_case, data, sub_schema, msg=msg, path=path)
                matched = True
                break
            except (AssertionError, Exception):
                continue
        if not matched:
            test_case.fail(
                f"{prefix}No oneOf branch matched at '{path}': value={data!r}"
            )
        return  # oneOf matched; skip remaining checks for this node

    # --- null passthrough ---
    if data is None:
        if schema_type and "null" not in (schema_type if isinstance(schema_type, list) else [schema_type]):
            test_case.fail(f"{prefix}Unexpected null at '{path}'")
        return

    # --- enum ---
    if "enum" in schema:
        test_case.assertIn(
            data, schema["enum"],
            f"{prefix}Enum violation at '{path}': {data!r} not in {schema['enum']}"
        )

    # --- minLength ---
    if "minLength" in schema and isinstance(data, str):
        test_case.assertGreaterEqual(
            len(data), schema["minLength"],
            f"{prefix}String too short at '{path}'"
        )

    # --- required ---
    if "required" in schema and isinstance(data, dict):
        for key in schema["required"]:
            test_case.assertIn(
                key, data,
                f"{prefix}Missing required key '{key}' at '{path}'"
            )

    # --- properties ---
    if "properties" in schema and isinstance(data, dict):
        for key, prop_schema in schema["properties"].items():
            if key in data:
                validate_schema(
                    test_case, data[key], prop_schema,
                    msg=msg, path=f"{path}.{key}" if path else key,
                )

    # --- additionalProperties ---
    additional = schema.get("additionalProperties")
    if additional is False and "properties" in schema and isinstance(data, dict):
        extra = set(data.keys()) - set(schema["properties"].keys())
        if extra:
            test_case.fail(
                f"{prefix}Unexpected keys at '{path}': {extra}"
            )
    elif isinstance(additional, dict) and isinstance(data, dict):
        for key, value in data.items():
            if key not in schema.get("properties", {}):
                validate_schema(
                    test_case, value, additional,
                    msg=msg, path=f"{path}.{key}" if path else key,
                )

    # --- items (array) ---
    if "items" in schema and isinstance(data, list):
        for idx, item in enumerate(data):
            validate_schema(
                test_case, item, schema["items"],
                msg=msg, path=f"{path}[{idx}]" if path else f"[{idx}]",
            )


# ---------------------------------------------------------------------------
# JSON Schemas matching TypeScript interfaces
# ---------------------------------------------------------------------------

USER_SCHEMA = {
    "type": "object",
    "required": [
        "id", "email", "first_name", "last_name", "role",
        "specialty", "license_number", "practice", "practice_name",
        "language_preference", "created_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "email": {"type": "string"},
        "first_name": {"type": "string"},
        "last_name": {"type": "string"},
        "role": {"type": "string", "enum": ["doctor", "admin", "patient"]},
        "specialty": {"type": "string"},
        "license_number": {"type": "string"},
        "practice": {"type": ["string", "null"]},
        "practice_name": {"type": ["string", "null"]},
        "language_preference": {"type": "string"},
        "created_at": {"type": "string"},
    },
    "additionalProperties": False,
}

LOGIN_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["access", "refresh", "user"],
    "properties": {
        "access": {"type": "string", "minLength": 1},
        "refresh": {"type": "string", "minLength": 1},
        "user": USER_SCHEMA,
    },
    "additionalProperties": False,
}

TOKEN_REFRESH_SCHEMA = {
    "type": "object",
    "required": ["access", "refresh"],
    "properties": {
        "access": {"type": "string", "minLength": 1},
        "refresh": {"type": "string", "minLength": 1},
    },
    "additionalProperties": True,
}

OTP_SEND_SCHEMA = {
    "type": "object",
    "required": ["message"],
    "properties": {
        "message": {"type": "string"},
    },
    "additionalProperties": False,
}

OTP_VERIFY_SCHEMA = {
    "type": "object",
    "required": ["access", "refresh", "user_id"],
    "properties": {
        "access": {"type": "string", "minLength": 1},
        "refresh": {"type": "string", "minLength": 1},
        "user_id": {"type": "string"},
    },
    "additionalProperties": False,
}

PATIENT_SCHEMA = {
    "type": "object",
    "required": [
        "id", "first_name", "last_name", "date_of_birth",
        "language_preference", "created_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "first_name": {"type": "string"},
        "last_name": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "date_of_birth": {"type": "string"},
        "language_preference": {"type": "string"},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
    },
    "additionalProperties": False,
}

PATIENT_LIST_ITEM_SCHEMA = {
    "type": "object",
    "required": ["id", "first_name", "last_name", "language_preference", "created_at"],
    "properties": {
        "id": {"type": "string"},
        "first_name": {"type": "string"},
        "last_name": {"type": "string"},
        "language_preference": {"type": "string"},
        "created_at": {"type": "string"},
    },
    "additionalProperties": False,
}

ENCOUNTER_SCHEMA = {
    "type": "object",
    "required": [
        "id", "doctor", "patient", "encounter_date", "input_method",
        "status", "consent_recording", "consent_timestamp", "consent_method",
        "consent_jurisdiction_state", "template_used", "created_at", "updated_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "doctor": {"type": "string"},
        "patient": {"type": "string"},
        "encounter_date": {"type": "string"},
        "input_method": {
            "type": "string",
            "enum": ["recording", "paste", "dictation", "scan", "telehealth"],
        },
        "status": {
            "type": "string",
            "enum": [
                "uploading", "transcribing", "generating_note",
                "generating_summary", "ready_for_review", "approved",
                "delivered", "transcription_failed", "note_generation_failed",
                "summary_generation_failed",
            ],
        },
        "consent_recording": {"type": "boolean"},
        "consent_timestamp": {"type": ["string", "null"]},
        "consent_method": {"type": "string"},
        "consent_jurisdiction_state": {"type": "string"},
        "template_used": {"type": ["string", "null"]},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
        # Detail-only fields (present only in retrieve)
        "has_recording": {"type": "boolean"},
        "has_transcript": {"type": "boolean"},
        "has_note": {"type": "boolean"},
        "has_summary": {"type": "boolean"},
        "has_telehealth": {"type": "boolean"},
        "has_quality_score": {"type": "boolean"},
    },
    "additionalProperties": False,
}

ENCOUNTER_DETAIL_SCHEMA = {
    **ENCOUNTER_SCHEMA,
    "required": ENCOUNTER_SCHEMA["required"] + [
        "has_recording", "has_transcript", "has_note", "has_summary",
        "has_telehealth", "has_quality_score",
    ],
}

TRANSCRIPT_SCHEMA = {
    "type": "object",
    "required": [
        "id", "raw_text", "speaker_segments", "medical_terms_detected",
        "confidence_score", "language_detected", "created_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "raw_text": {"type": "string"},
        "speaker_segments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["speaker", "start", "end", "text"],
                "properties": {
                    "speaker": {"type": "string"},
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "text": {"type": "string"},
                },
            },
        },
        "medical_terms_detected": {
            "type": "array",
            "items": {"type": "string"},
        },
        "confidence_score": {"type": "number"},
        "language_detected": {"type": "string"},
        "created_at": {"type": "string"},
    },
    "additionalProperties": False,
}

PROMPT_VERSION_SCHEMA = {
    "type": "object",
    "required": ["id", "prompt_name", "version", "is_active", "created_at"],
    "properties": {
        "id": {"type": "string"},
        "prompt_name": {"type": "string"},
        "version": {"type": "string"},
        "is_active": {"type": "boolean"},
        "created_at": {"type": "string"},
    },
    "additionalProperties": False,
}

CLINICAL_NOTE_SCHEMA = {
    "type": "object",
    "required": [
        "id", "encounter", "note_type", "subjective", "objective",
        "assessment", "plan", "raw_content", "icd10_codes", "cpt_codes",
        "ai_generated", "doctor_edited", "approved_at", "approved_by",
        "prompt_version", "prompt_version_detail", "created_at", "updated_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "encounter": {"type": "string"},
        "note_type": {"type": "string", "enum": ["soap", "free_text", "h_and_p"]},
        "subjective": {"type": "string"},
        "objective": {"type": "string"},
        "assessment": {"type": "string"},
        "plan": {"type": "string"},
        "raw_content": {"type": "string"},
        "icd10_codes": {"type": "array", "items": {"type": "string"}},
        "cpt_codes": {"type": "array", "items": {"type": "string"}},
        "ai_generated": {"type": "boolean"},
        "doctor_edited": {"type": "boolean"},
        "approved_at": {"type": ["string", "null"]},
        "approved_by": {"type": ["string", "null"]},
        "prompt_version": {"type": ["string", "null"]},
        "prompt_version_detail": {
            "oneOf": [
                {"type": "null"},
                PROMPT_VERSION_SCHEMA,
            ],
        },
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
    },
    "additionalProperties": False,
}

DOCTOR_SUMMARY_SCHEMA = {
    "type": "object",
    "required": [
        "id", "encounter", "clinical_note", "summary_en", "summary_es",
        "reading_level", "medical_terms_explained", "disclaimer_text",
        "delivery_status", "delivered_at", "viewed_at", "delivery_method",
        "prompt_version", "created_at", "updated_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "encounter": {"type": "string"},
        "clinical_note": {"type": "string"},
        "summary_en": {"type": "string"},
        "summary_es": {"type": "string"},
        "reading_level": {"type": "string", "enum": ["grade_5", "grade_8", "grade_12"]},
        "medical_terms_explained": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["term", "explanation"],
                "properties": {
                    "term": {"type": "string"},
                    "explanation": {"type": "string"},
                },
            },
        },
        "disclaimer_text": {"type": "string"},
        "delivery_status": {
            "type": "string",
            "enum": ["pending", "sent", "viewed", "failed"],
        },
        "delivered_at": {"type": ["string", "null"]},
        "viewed_at": {"type": ["string", "null"]},
        "delivery_method": {"type": "string"},
        "prompt_version": {"type": ["string", "null"]},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
    },
    "additionalProperties": False,
}

# Patient-facing / Widget summary: matches mobile PatientSummary and widget WidgetSummaryData
PATIENT_FACING_SUMMARY_SCHEMA = {
    "type": "object",
    "required": [
        "id", "summary_en", "summary_es", "reading_level",
        "medical_terms_explained", "disclaimer_text",
        "encounter_date", "doctor_name", "delivery_status",
        "viewed_at", "created_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "summary_en": {"type": "string"},
        "summary_es": {"type": "string"},
        "reading_level": {"type": "string", "enum": ["grade_5", "grade_8", "grade_12"]},
        "medical_terms_explained": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["term", "explanation"],
                "properties": {
                    "term": {"type": "string"},
                    "explanation": {"type": "string"},
                },
            },
        },
        "disclaimer_text": {"type": "string"},
        "encounter_date": {"type": "string"},
        "doctor_name": {"type": "string"},
        "delivery_status": {
            "type": "string",
            "enum": ["pending", "sent", "viewed", "failed"],
        },
        "viewed_at": {"type": ["string", "null"]},
        "created_at": {"type": "string"},
    },
    "additionalProperties": False,
}

WIDGET_CONFIG_SCHEMA = {
    "type": "object",
    "required": ["practice_name", "widget_key"],
    "properties": {
        "practice_name": {"type": "string"},
        "widget_key": {"type": "string"},
        "logo_url": {"type": "string"},
        "brand_color": {"type": "string"},
        "custom_domain": {"type": "string"},
    },
    "additionalProperties": True,
}

PAGINATED_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["count", "next", "previous", "results"],
    "properties": {
        "count": {"type": "integer"},
        "next": {"type": ["string", "null"]},
        "previous": {"type": ["string", "null"]},
        "results": {"type": "array"},
    },
}

PATIENT_SUMMARY_LIST_SCHEMA = {
    "type": "object",
    "required": ["count", "results"],
    "properties": {
        "count": {"type": "integer"},
        "results": {
            "type": "array",
            "items": PATIENT_FACING_SUMMARY_SCHEMA,
        },
    },
}

PRACTICE_SCHEMA = {
    "type": "object",
    "required": [
        "id", "name", "address", "phone", "subscription_tier",
        "white_label_config", "created_at", "updated_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "address": {"type": "string"},
        "phone": {"type": "string"},
        "subscription_tier": {
            "type": "string",
            "enum": ["solo", "group", "enterprise"],
        },
        "white_label_config": {"type": ["object", "null"]},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
    },
    "additionalProperties": False,
}

PRACTICE_STATS_SCHEMA = {
    "type": "object",
    "required": ["total_patients", "total_encounters", "encounters_by_status"],
    "properties": {
        "total_patients": {"type": "integer"},
        "total_encounters": {"type": "integer"},
        "encounters_by_status": {
            "type": "object",
            "additionalProperties": {"type": "integer"},
        },
    },
    "additionalProperties": False,
}

AUDIT_LOG_ENTRY_SCHEMA = {
    "type": "object",
    "required": [
        "id", "user_email", "action", "resource_type",
        "resource_id", "ip_address", "phi_accessed", "created_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "user_email": {"type": "string"},
        "action": {"type": "string"},
        "resource_type": {"type": "string"},
        "resource_id": {"type": "string"},
        "ip_address": {"type": "string"},
        "phi_accessed": {"type": "boolean"},
        "created_at": {"type": "string"},
    },
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION="none",
)
class BaseSchemaTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.practice = Practice.objects.create(
            name="Schema Clinic",
            subscription_tier="solo",
        )
        cls.doctor = User.objects.create_user(
            email="schema_doc@test.com",
            password="Str0ngP@ssw0rd!",
            role="doctor",
            first_name="Schema",
            last_name="Doc",
            practice=cls.practice,
        )
        cls.patient_record = Patient.objects.create(
            practice=cls.practice,
            first_name="Schema",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            phone="+15550001111",
            email="schemapat@test.com",
        )

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(user=self.doctor)


# ===========================================================================
# Schema validation tests
# ===========================================================================

class UserSchemaTests(BaseSchemaTest):

    def test_login_response_matches_schema(self):
        from unittest.mock import patch as _patch
        from dj_rest_auth.app_settings import api_settings
        with _patch.object(api_settings, "JWT_AUTH_HTTPONLY", False):
            client = APIClient()
            resp = client.post("/api/v1/auth/login/", {
                "email": "schema_doc@test.com",
                "password": "Str0ngP@ssw0rd!",
            }, format="json")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, LOGIN_RESPONSE_SCHEMA, "LoginResponse")

    def test_get_user_matches_schema(self):
        resp = self.api.get("/api/v1/auth/user/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, USER_SCHEMA, "User")

    def test_token_refresh_matches_schema(self):
        from unittest.mock import patch as _patch
        from dj_rest_auth.app_settings import api_settings
        with _patch.object(api_settings, "JWT_AUTH_HTTPONLY", False):
            client = APIClient()
            login = client.post("/api/v1/auth/login/", {
                "email": "schema_doc@test.com",
                "password": "Str0ngP@ssw0rd!",
            }, format="json")
            resp = client.post("/api/v1/auth/token/refresh/", {
                "refresh": login.data["refresh"],
            }, format="json")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, TOKEN_REFRESH_SCHEMA, "TokenRefreshResponse")

    def test_register_response_matches_schema(self):
        from unittest.mock import patch as _patch
        from dj_rest_auth.app_settings import api_settings
        with _patch.object(api_settings, "JWT_AUTH_HTTPONLY", False):
            client = APIClient()
            resp = client.post("/api/v1/auth/registration/", {
                "email": "schemareg@test.com",
                "password1": "Str0ngP@ssw0rd!",
                "password2": "Str0ngP@ssw0rd!",
                "first_name": "Reg",
                "last_name": "User",
                "practice_name": "Reg Practice",
            }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        validate_schema(self, resp.data, LOGIN_RESPONSE_SCHEMA, "Registration/LoginResponse")


class OTPSchemaTests(BaseSchemaTest):

    @patch("services.notification_service.NotificationService")
    def test_otp_send_matches_schema(self, mock_sms_cls):
        mock_sms_cls.return_value = MagicMock()
        client = APIClient()
        resp = client.post("/api/v1/auth/patient/otp/send/", {
            "phone": "+15550001111",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, OTP_SEND_SCHEMA, "OTPSendResponse")

    def test_otp_verify_matches_schema(self):
        phone = "+15550009999"
        cache.set(f"otp:{phone}", "654321", timeout=300)
        cache.set(f"otp_attempts:{phone}", 0, timeout=300)

        client = APIClient()
        resp = client.post("/api/v1/auth/patient/otp/verify/", {
            "phone": phone,
            "code": "654321",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, OTP_VERIFY_SCHEMA, "OTPVerifyResponse")


class PatientSchemaTests(BaseSchemaTest):

    def test_create_patient_matches_schema(self):
        resp = self.api.post("/api/v1/patients/", {
            "first_name": "Schema",
            "last_name": "PatCreate",
            "date_of_birth": "1995-06-01",
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        validate_schema(self, resp.data, PATIENT_SCHEMA, "Patient (create)")

    def test_retrieve_patient_matches_schema(self):
        resp = self.api.get(f"/api/v1/patients/{self.patient_record.id}/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, PATIENT_SCHEMA, "Patient (retrieve)")

    def test_list_patients_matches_paginated_schema(self):
        resp = self.api.get("/api/v1/patients/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, PAGINATED_RESPONSE_SCHEMA, "PaginatedResponse<PatientListItem>")
        for item in resp.data["results"]:
            validate_schema(self, item, PATIENT_LIST_ITEM_SCHEMA, "PatientListItem")


class EncounterSchemaTests(BaseSchemaTest):

    def test_create_encounter_matches_schema(self):
        resp = self.api.post("/api/v1/encounters/", {
            "patient": str(self.patient_record.id),
            "encounter_date": "2026-03-15",
            "input_method": "paste",
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        validate_schema(self, resp.data, ENCOUNTER_SCHEMA, "Encounter (create)")

    def test_list_encounters_matches_paginated_schema(self):
        Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        resp = self.api.get("/api/v1/encounters/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, PAGINATED_RESPONSE_SCHEMA, "PaginatedResponse<Encounter>")
        for item in resp.data["results"]:
            validate_schema(self, item, ENCOUNTER_SCHEMA, "Encounter (list item)")

    def test_retrieve_encounter_matches_detail_schema(self):
        enc = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        resp = self.api.get(f"/api/v1/encounters/{enc.id}/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, ENCOUNTER_DETAIL_SCHEMA, "EncounterDetail")

    def test_transcript_matches_schema(self):
        enc = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        Transcript.objects.create(
            encounter=enc,
            raw_text="Some transcript text.",
            speaker_segments=[
                {"speaker": "doctor", "start": 0.0, "end": 3.5, "text": "Hello there."},
            ],
            medical_terms_detected=["headache"],
            confidence_score=0.92,
            language_detected="en",
        )
        resp = self.api.get(f"/api/v1/encounters/{enc.id}/transcript/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, TRANSCRIPT_SCHEMA, "Transcript")


class ClinicalNoteSchemaTests(BaseSchemaTest):

    def setUp(self):
        super().setUp()
        self.pv = PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="Test prompt",
            is_active=True,
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
            status="ready_for_review",
        )
        self.note = ClinicalNote.objects.create(
            encounter=self.encounter,
            note_type="soap",
            subjective="Patient reports pain.",
            objective="Vitals normal.",
            assessment="Muscle strain.",
            plan="Rest and ice.",
            raw_content="Full note content.",
            icd10_codes=["M54.5"],
            cpt_codes=["99213"],
            ai_generated=True,
            prompt_version=self.pv,
        )

    def test_get_note_matches_schema(self):
        resp = self.api.get(f"/api/v1/encounters/{self.encounter.id}/note/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, CLINICAL_NOTE_SCHEMA, "ClinicalNote (GET)")

    def test_update_note_matches_schema(self):
        resp = self.api.patch(
            f"/api/v1/encounters/{self.encounter.id}/note/",
            {"subjective": "Updated pain report."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, CLINICAL_NOTE_SCHEMA, "ClinicalNote (PATCH)")

    def test_approve_note_matches_schema(self):
        resp = self.api.post(f"/api/v1/encounters/{self.encounter.id}/note/approve/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, CLINICAL_NOTE_SCHEMA, "ClinicalNote (approve)")
        # approved_at should now be a string, not null
        self.assertIsNotNone(resp.data["approved_at"])

    def test_prompt_version_detail_matches_schema(self):
        """When prompt_version is set, prompt_version_detail must match PromptVersion schema."""
        resp = self.api.get(f"/api/v1/encounters/{self.encounter.id}/note/")
        self.assertEqual(resp.status_code, 200)
        pv_detail = resp.data["prompt_version_detail"]
        self.assertIsNotNone(pv_detail)
        validate_schema(self, pv_detail, PROMPT_VERSION_SCHEMA, "PromptVersion")

    def test_note_without_prompt_version(self):
        """When no prompt_version, the field should be null."""
        self.note.prompt_version = None
        self.note.save(update_fields=["prompt_version"])
        resp = self.api.get(f"/api/v1/encounters/{self.encounter.id}/note/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["prompt_version"])
        self.assertIsNone(resp.data["prompt_version_detail"])


class DoctorSummarySchemaTests(BaseSchemaTest):

    def setUp(self):
        super().setUp()
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
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
        self.summary = PatientSummary.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            summary_en="Your summary in English.",
            summary_es="Su resumen en espanol.",
            reading_level="grade_8",
            medical_terms_explained=[
                {"term": "hypertension", "explanation": "high blood pressure"},
            ],
            delivery_status="pending",
        )

    def test_get_summary_matches_schema(self):
        resp = self.api.get(f"/api/v1/encounters/{self.encounter.id}/summary/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, DOCTOR_SUMMARY_SCHEMA, "PatientSummary (GET)")

    def test_send_summary_matches_schema(self):
        resp = self.api.post(
            f"/api/v1/encounters/{self.encounter.id}/summary/send/",
            {"delivery_method": "widget"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, DOCTOR_SUMMARY_SCHEMA, "PatientSummary (send)")

    def test_medical_terms_explained_shape(self):
        """Each item in medical_terms_explained has {term, explanation}."""
        resp = self.api.get(f"/api/v1/encounters/{self.encounter.id}/summary/")
        terms = resp.data["medical_terms_explained"]
        self.assertEqual(len(terms), 1)
        self.assertEqual(terms[0]["term"], "hypertension")
        self.assertIsInstance(terms[0]["explanation"], str)


class PatientFacingSummarySchemaTests(BaseSchemaTest):

    def setUp(self):
        super().setUp()
        self.patient_user = User.objects.create_user(
            email="+15550001111@patient.medicalnote.local",
            role="patient",
            phone="+15550001111",
        )
        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
            status="delivered",
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
        self.summary = PatientSummary.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            summary_en="Patient facing EN.",
            summary_es="Patient facing ES.",
            reading_level="grade_5",
            medical_terms_explained=[],
            delivery_status="sent",
        )
        self.api.force_authenticate(user=self.patient_user)

    def test_patient_summary_list_matches_schema(self):
        resp = self.api.get("/api/v1/patient/summaries/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, PATIENT_SUMMARY_LIST_SCHEMA, "PatientSummaryListResponse")

    def test_patient_summary_detail_matches_schema(self):
        resp = self.api.get(f"/api/v1/patient/summaries/{self.summary.id}/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, PATIENT_FACING_SUMMARY_SCHEMA, "PatientSummary (detail)")

    def test_patient_summary_has_doctor_name(self):
        """doctor_name field must follow 'Dr. LastName' convention."""
        resp = self.api.get(f"/api/v1/patient/summaries/{self.summary.id}/")
        self.assertIn("Dr.", resp.data["doctor_name"])


class WidgetSchemaTests(BaseSchemaTest):

    def setUp(self):
        super().setUp()
        self.practice.white_label_config = {
            "widget_key": "schema-widget-key",
            "logo_url": "https://example.com/logo.png",
            "brand_color": "#ff5722",
            "custom_domain": "schema.example.com",
        }
        self.practice.save()

        self.encounter = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
            status="delivered",
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
        self.summary = PatientSummary.objects.create(
            encounter=self.encounter,
            clinical_note=self.note,
            summary_en="Widget schema test EN.",
            summary_es="Widget schema test ES.",
            reading_level="grade_12",
            delivery_status="sent",
        )

    def test_widget_config_matches_schema(self):
        client = APIClient()
        resp = client.get("/api/v1/widget/config/schema-widget-key/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, WIDGET_CONFIG_SCHEMA, "WidgetBrandConfig")

    def test_widget_summary_matches_schema(self):
        signer = TimestampSigner()
        token = signer.sign(str(self.summary.id))
        client = APIClient()
        resp = client.get(f"/api/v1/widget/summary/{token}/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, PATIENT_FACING_SUMMARY_SCHEMA, "WidgetSummaryData")

    def test_widget_summary_data_matches_widget_types(self):
        """Verify the WidgetSummaryData shape exactly matches widget/src/types.ts."""
        signer = TimestampSigner()
        token = signer.sign(str(self.summary.id))
        client = APIClient()
        resp = client.get(f"/api/v1/widget/summary/{token}/")
        data = resp.data
        # Required by widget/src/types.ts WidgetSummaryData
        required_fields = [
            "id", "summary_en", "summary_es", "reading_level",
            "medical_terms_explained", "disclaimer_text", "encounter_date",
            "doctor_name", "delivery_status", "viewed_at", "created_at",
        ]
        for field in required_fields:
            self.assertIn(field, data, f"Missing WidgetSummaryData field: {field}")


class PracticeSchemaTests(BaseSchemaTest):

    def test_practice_get_matches_schema(self):
        resp = self.api.get("/api/v1/practice/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, PRACTICE_SCHEMA, "Practice")

    def test_practice_update_matches_schema(self):
        resp = self.api.patch("/api/v1/practice/", {
            "address": "123 Test St",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, PRACTICE_SCHEMA, "Practice (updated)")

    def test_practice_stats_matches_schema(self):
        resp = self.api.get("/api/v1/practice/stats/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, PRACTICE_STATS_SCHEMA, "PracticeStats")


class AuditLogSchemaTests(BaseSchemaTest):

    def setUp(self):
        super().setUp()
        # Audit log requires admin role
        self.admin = User.objects.create_user(
            email="schema_admin@test.com",
            password="Adm1nP@ssw0rd!",
            role="admin",
            practice=self.practice,
        )

    def test_audit_log_list_matches_paginated_schema(self):
        # Trigger an audit log entry by accessing a PHI endpoint
        self.api.force_authenticate(user=self.doctor)
        self.api.get("/api/v1/patients/")

        # Now access audit log as admin
        self.api.force_authenticate(user=self.admin)
        resp = self.api.get("/api/v1/practice/audit-log/")
        self.assertEqual(resp.status_code, 200)
        validate_schema(self, resp.data, PAGINATED_RESPONSE_SCHEMA, "PaginatedResponse<AuditLogEntry>")
        if resp.data["results"]:
            validate_schema(
                self, resp.data["results"][0],
                AUDIT_LOG_ENTRY_SCHEMA,
                "AuditLogEntry",
            )
