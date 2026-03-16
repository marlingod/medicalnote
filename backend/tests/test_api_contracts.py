"""
API Contract Tests
==================
Verify that ALL backend endpoints return response shapes matching what the
three frontend clients (web, mobile, widget) expect.

Each test method validates:
  - HTTP status code
  - JSON structure (required keys)
  - Field types (str, int, list, bool, None-or-str, etc.)
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
# Helpers
# ---------------------------------------------------------------------------

def _uuid_str(val):
    """Return True when *val* looks like a UUID string."""
    if not isinstance(val, str):
        return False
    import re
    return bool(re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        val,
    ))


def _iso_datetime(val):
    """Return True when *val* is an ISO-8601 datetime string or None."""
    if val is None:
        return True
    if not isinstance(val, str):
        return False
    from datetime import datetime
    try:
        datetime.fromisoformat(val.replace("Z", "+00:00"))
        return True
    except (ValueError, TypeError):
        return False


def _iso_date(val):
    """Return True when *val* is an ISO date string (YYYY-MM-DD)."""
    if not isinstance(val, str):
        return False
    import re
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", val))


def _assert_keys(test_case, data, required_keys):
    """Assert that *data* contains every key in *required_keys*."""
    for key in required_keys:
        test_case.assertIn(key, data, f"Missing required key: '{key}'")


# ---------------------------------------------------------------------------
# Shared test scaffolding
# ---------------------------------------------------------------------------

@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION="none",
)
class BaseContractTest(TestCase):
    """Provides a doctor user, a patient record, and common fixtures."""

    @classmethod
    def setUpTestData(cls):
        cls.practice = Practice.objects.create(
            name="ContractTest Clinic",
            subscription_tier="solo",
        )
        cls.doctor = User.objects.create_user(
            email="contract_doc@test.com",
            password="SecureTestP@ss1",
            role="doctor",
            first_name="Alice",
            last_name="Contract",
            practice=cls.practice,
        )
        cls.patient_record = Patient.objects.create(
            practice=cls.practice,
            first_name="Bob",
            last_name="Patient",
            date_of_birth=date(1985, 6, 15),
            phone="+15559990000",
            email="bob@patient.test",
        )

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(user=self.doctor)


# ===========================================================================
# 1. AUTH FLOW CONTRACTS
# ===========================================================================

class AuthContractTests(BaseContractTest):
    """
    Validates response shapes for:
      POST /api/v1/auth/registration/
      POST /api/v1/auth/login/
      GET  /api/v1/auth/user/
      POST /api/v1/auth/token/refresh/
      POST /api/v1/auth/logout/
    """

    def test_register_returns_jwt_tokens(self):
        """Registration response must include access + refresh tokens.

        Corresponds to web RegisterRequest -> LoginResponse contract.
        """
        client = APIClient()
        resp = client.post("/api/v1/auth/registration/", {
            "email": "newdoc@contract.test",
            "password1": "VeryStr0ngP@ss!",
            "password2": "VeryStr0ngP@ss!",
            "first_name": "New",
            "last_name": "Doctor",
            "practice_name": "Fresh Practice",
        }, format="json")

        self.assertEqual(resp.status_code, 201, resp.data)
        _assert_keys(self, resp.data, ["access", "refresh", "user"])
        self.assertIsInstance(resp.data["access"], str)
        self.assertIsInstance(resp.data["refresh"], str)
        # User sub-object matches web User interface
        user_data = resp.data["user"]
        self._assert_user_shape(user_data)

    def test_login_returns_tokens_and_user(self):
        """POST /api/v1/auth/login/ -> LoginResponse {access, refresh, user}"""
        client = APIClient()
        resp = client.post("/api/v1/auth/login/", {
            "email": "contract_doc@test.com",
            "password": "SecureTestP@ss1",
        }, format="json")

        self.assertEqual(resp.status_code, 200, resp.data)
        _assert_keys(self, resp.data, ["access", "refresh", "user"])
        self.assertIsInstance(resp.data["access"], str)
        self.assertIsInstance(resp.data["refresh"], str)
        self._assert_user_shape(resp.data["user"])

    def test_get_user_response_shape(self):
        """GET /api/v1/auth/user/ -> User interface."""
        resp = self.api.get("/api/v1/auth/user/")
        self.assertEqual(resp.status_code, 200)
        self._assert_user_shape(resp.data)

    def test_token_refresh_response_shape(self):
        """POST /api/v1/auth/token/refresh/ -> TokenRefreshResponse."""
        # Obtain a valid refresh token first
        client = APIClient()
        login_resp = client.post("/api/v1/auth/login/", {
            "email": "contract_doc@test.com",
            "password": "SecureTestP@ss1",
        }, format="json")
        refresh_token = login_resp.data["refresh"]

        resp = client.post("/api/v1/auth/token/refresh/", {
            "refresh": refresh_token,
        }, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        _assert_keys(self, resp.data, ["access", "refresh"])
        self.assertIsInstance(resp.data["access"], str)
        self.assertIsInstance(resp.data["refresh"], str)

    def test_logout_succeeds(self):
        """POST /api/v1/auth/logout/ returns 200."""
        resp = self.api.post("/api/v1/auth/logout/")
        self.assertIn(resp.status_code, [200, 204])

    # -- helpers --
    def _assert_user_shape(self, data):
        """Validate User matches web/src/types/index.ts User interface."""
        user_fields = [
            "id", "email", "first_name", "last_name", "role",
            "specialty", "license_number", "practice", "practice_name",
            "language_preference", "created_at",
        ]
        _assert_keys(self, data, user_fields)
        self.assertIsInstance(data["email"], str)
        self.assertIn(data["role"], ["doctor", "admin", "patient"])
        self.assertIsInstance(data["first_name"], str)
        self.assertIsInstance(data["last_name"], str)
        self.assertIsInstance(data["specialty"], str)
        self.assertIsInstance(data["license_number"], str)
        self.assertIsInstance(data["language_preference"], str)
        self.assertTrue(_iso_datetime(data["created_at"]))
        # practice is uuid-string or None
        if data["practice"] is not None:
            self.assertTrue(_uuid_str(data["practice"]))
        # practice_name is str or None
        self.assertTrue(
            data["practice_name"] is None or isinstance(data["practice_name"], str)
        )


# ===========================================================================
# 2. PATIENT FLOW CONTRACTS (OTP)
# ===========================================================================

class PatientOTPContractTests(BaseContractTest):
    """
    Validates:
      POST /api/v1/auth/patient/otp/send/   -> OTPSendResponse {message}
      POST /api/v1/auth/patient/otp/verify/  -> OTPVerifyResponse {access, refresh, user_id}
    """

    @patch("apps.accounts.adapters.NotificationService")
    def test_otp_send_response_shape(self, mock_sms_cls):
        """OTP send returns {message: str}."""
        mock_sms_cls.return_value = MagicMock()
        client = APIClient()
        resp = client.post("/api/v1/auth/patient/otp/send/", {
            "phone": "+15559990000",
        }, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        _assert_keys(self, resp.data, ["message"])
        self.assertIsInstance(resp.data["message"], str)

    @patch("apps.accounts.adapters.NotificationService")
    def test_otp_verify_response_shape(self, mock_sms_cls):
        """OTP verify returns {access, refresh, user_id}."""
        mock_sms_cls.return_value = MagicMock()
        phone = "+15559990001"
        # Put a code in cache to simulate send
        cache.set(f"otp:{phone}", "123456", timeout=300)
        cache.set(f"otp_attempts:{phone}", 0, timeout=300)

        client = APIClient()
        resp = client.post("/api/v1/auth/patient/otp/verify/", {
            "phone": phone,
            "code": "123456",
        }, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        _assert_keys(self, resp.data, ["access", "refresh", "user_id"])
        self.assertIsInstance(resp.data["access"], str)
        self.assertIsInstance(resp.data["refresh"], str)
        self.assertIsInstance(resp.data["user_id"], str)

    def test_otp_send_missing_phone_returns_400(self):
        client = APIClient()
        resp = client.post("/api/v1/auth/patient/otp/send/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        _assert_keys(self, resp.data, ["error"])

    def test_otp_verify_invalid_code_returns_401(self):
        phone = "+15559990002"
        cache.set(f"otp:{phone}", "999999", timeout=300)
        cache.set(f"otp_attempts:{phone}", 0, timeout=300)

        client = APIClient()
        resp = client.post("/api/v1/auth/patient/otp/verify/", {
            "phone": phone,
            "code": "000000",
        }, format="json")
        self.assertEqual(resp.status_code, 401)
        _assert_keys(self, resp.data, ["error"])


# ===========================================================================
# 3. PATIENT CRUD CONTRACTS
# ===========================================================================

class PatientCRUDContractTests(BaseContractTest):
    """
    Validates:
      POST   /api/v1/patients/        -> Patient
      GET    /api/v1/patients/         -> PaginatedResponse<PatientListItem>
      GET    /api/v1/patients/:id/     -> Patient
      PATCH  /api/v1/patients/:id/     -> Patient
      DELETE /api/v1/patients/:id/     -> 204
    """

    PATIENT_FIELDS = [
        "id", "first_name", "last_name", "email", "phone",
        "date_of_birth", "language_preference", "created_at", "updated_at",
    ]
    PATIENT_LIST_FIELDS = [
        "id", "first_name", "last_name", "language_preference", "created_at",
    ]

    def test_create_patient_response_shape(self):
        resp = self.api.post("/api/v1/patients/", {
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1992-03-10",
            "phone": "+15551112222",
            "email": "jane@test.com",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        _assert_keys(self, resp.data, self.PATIENT_FIELDS)
        self.assertTrue(_uuid_str(resp.data["id"]))
        self.assertEqual(resp.data["first_name"], "Jane")
        self.assertIsInstance(resp.data["date_of_birth"], str)
        self.assertTrue(_iso_datetime(resp.data["created_at"]))

    def test_list_patients_paginated_response(self):
        resp = self.api.get("/api/v1/patients/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, ["count", "next", "previous", "results"])
        self.assertIsInstance(resp.data["count"], int)
        self.assertIsInstance(resp.data["results"], list)
        if resp.data["results"]:
            item = resp.data["results"][0]
            _assert_keys(self, item, self.PATIENT_LIST_FIELDS)

    def test_retrieve_patient_response_shape(self):
        resp = self.api.get(f"/api/v1/patients/{self.patient_record.id}/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, self.PATIENT_FIELDS)
        self.assertTrue(_uuid_str(resp.data["id"]))

    def test_update_patient_response_shape(self):
        resp = self.api.patch(
            f"/api/v1/patients/{self.patient_record.id}/",
            {"first_name": "Robert"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, self.PATIENT_FIELDS)
        self.assertEqual(resp.data["first_name"], "Robert")

    def test_delete_patient_returns_204(self):
        tmp = Patient.objects.create(
            practice=self.practice,
            first_name="Temp",
            last_name="Delete",
            date_of_birth=date(2000, 1, 1),
        )
        resp = self.api.delete(f"/api/v1/patients/{tmp.id}/")
        self.assertEqual(resp.status_code, 204)


# ===========================================================================
# 4. ENCOUNTER CONTRACTS
# ===========================================================================

class EncounterContractTests(BaseContractTest):
    """
    Validates:
      POST   /api/v1/encounters/                     -> Encounter
      GET    /api/v1/encounters/                      -> PaginatedResponse<Encounter>
      GET    /api/v1/encounters/:id/                  -> EncounterDetail
      PATCH  /api/v1/encounters/:id/                  -> Encounter
      DELETE /api/v1/encounters/:id/                  -> 204
      POST   /api/v1/encounters/:id/paste/            -> {status, encounter_id}
      POST   /api/v1/encounters/:id/dictation/        -> {status, encounter_id}
      GET    /api/v1/encounters/:id/transcript/       -> Transcript
    """

    ENCOUNTER_FIELDS = [
        "id", "doctor", "patient", "encounter_date", "input_method",
        "status", "consent_recording", "consent_timestamp", "consent_method",
        "consent_jurisdiction_state", "created_at", "updated_at",
    ]
    ENCOUNTER_DETAIL_EXTRA = [
        "has_recording", "has_transcript", "has_note", "has_summary",
    ]
    ENCOUNTER_STATUSES = [
        "uploading", "transcribing", "generating_note", "generating_summary",
        "ready_for_review", "approved", "delivered",
        "transcription_failed", "note_generation_failed", "summary_generation_failed",
    ]
    INPUT_METHODS = ["recording", "paste", "dictation", "scan"]

    def test_create_encounter_response_shape(self):
        resp = self.api.post("/api/v1/encounters/", {
            "patient": str(self.patient_record.id),
            "encounter_date": "2026-03-15",
            "input_method": "paste",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        data = resp.data
        _assert_keys(self, data, self.ENCOUNTER_FIELDS)
        self.assertTrue(_uuid_str(data["id"]))
        self.assertTrue(_uuid_str(data["doctor"]))
        self.assertTrue(_uuid_str(data["patient"]))
        self.assertIn(data["status"], self.ENCOUNTER_STATUSES)
        self.assertIn(data["input_method"], self.INPUT_METHODS)
        self.assertIsInstance(data["consent_recording"], bool)
        self.assertTrue(_iso_datetime(data["created_at"]))

    def test_list_encounters_paginated(self):
        Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        resp = self.api.get("/api/v1/encounters/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, ["count", "next", "previous", "results"])
        self.assertIsInstance(resp.data["results"], list)
        self.assertGreater(len(resp.data["results"]), 0)
        _assert_keys(self, resp.data["results"][0], self.ENCOUNTER_FIELDS)

    def test_retrieve_encounter_detail_shape(self):
        enc = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        resp = self.api.get(f"/api/v1/encounters/{enc.id}/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, self.ENCOUNTER_FIELDS + self.ENCOUNTER_DETAIL_EXTRA)
        self.assertIsInstance(resp.data["has_recording"], bool)
        self.assertIsInstance(resp.data["has_transcript"], bool)
        self.assertIsInstance(resp.data["has_note"], bool)
        self.assertIsInstance(resp.data["has_summary"], bool)

    @patch("workers.soap_note.generate_soap_note_task.delay")
    def test_paste_input_response_shape(self, mock_task):
        enc = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        resp = self.api.post(f"/api/v1/encounters/{enc.id}/paste/", {
            "text": "Patient presents with persistent cough for 5 days. No fever.",
        }, format="json")
        self.assertEqual(resp.status_code, 202, resp.data)
        _assert_keys(self, resp.data, ["status", "encounter_id"])
        self.assertIsInstance(resp.data["status"], str)
        self.assertIsInstance(resp.data["encounter_id"], str)

    @patch("workers.soap_note.generate_soap_note_task.delay")
    def test_dictation_input_response_shape(self, mock_task):
        enc = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="dictation",
        )
        resp = self.api.post(f"/api/v1/encounters/{enc.id}/dictation/", {
            "text": "Dictation note: patient complains of lower back pain for two weeks.",
        }, format="json")
        self.assertEqual(resp.status_code, 202, resp.data)
        _assert_keys(self, resp.data, ["status", "encounter_id"])

    def test_get_transcript_response_shape(self):
        enc = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        Transcript.objects.create(
            encounter=enc,
            raw_text="Test transcript text.",
            speaker_segments=[{"speaker": "doctor", "start": 0, "end": 5, "text": "Hello"}],
            medical_terms_detected=["cough"],
            confidence_score=0.95,
            language_detected="en",
        )
        resp = self.api.get(f"/api/v1/encounters/{enc.id}/transcript/")
        self.assertEqual(resp.status_code, 200)
        transcript_fields = [
            "id", "raw_text", "speaker_segments", "medical_terms_detected",
            "confidence_score", "language_detected", "created_at",
        ]
        _assert_keys(self, resp.data, transcript_fields)
        self.assertIsInstance(resp.data["raw_text"], str)
        self.assertIsInstance(resp.data["speaker_segments"], list)
        self.assertIsInstance(resp.data["medical_terms_detected"], list)
        self.assertIsInstance(resp.data["confidence_score"], float)

    def test_get_transcript_404_when_missing(self):
        enc = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        resp = self.api.get(f"/api/v1/encounters/{enc.id}/transcript/")
        self.assertEqual(resp.status_code, 404)
        _assert_keys(self, resp.data, ["error"])

    def test_update_encounter_response_shape(self):
        enc = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        resp = self.api.patch(
            f"/api/v1/encounters/{enc.id}/",
            {"consent_recording": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, self.ENCOUNTER_FIELDS)
        self.assertTrue(resp.data["consent_recording"])

    def test_delete_encounter_returns_204(self):
        enc = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        resp = self.api.delete(f"/api/v1/encounters/{enc.id}/")
        self.assertEqual(resp.status_code, 204)


# ===========================================================================
# 5. CLINICAL NOTE CONTRACTS
# ===========================================================================

class ClinicalNoteContractTests(BaseContractTest):
    """
    Validates:
      GET   /api/v1/encounters/:id/note/         -> ClinicalNote
      PATCH /api/v1/encounters/:id/note/         -> ClinicalNote
      POST  /api/v1/encounters/:id/note/approve/ -> ClinicalNote
    """

    NOTE_FIELDS = [
        "id", "encounter", "note_type", "subjective", "objective",
        "assessment", "plan", "raw_content", "icd10_codes", "cpt_codes",
        "ai_generated", "doctor_edited", "approved_at", "approved_by",
        "prompt_version", "prompt_version_detail", "created_at", "updated_at",
    ]
    NOTE_TYPES = ["soap", "free_text", "h_and_p"]

    def setUp(self):
        super().setUp()
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
            subjective="Patient has headache.",
            objective="BP 120/80.",
            assessment="Tension headache.",
            plan="Ibuprofen PRN.",
            raw_content="Full SOAP content.",
            icd10_codes=["R51.9"],
            cpt_codes=["99214"],
            ai_generated=True,
        )

    def test_get_note_response_shape(self):
        resp = self.api.get(f"/api/v1/encounters/{self.encounter.id}/note/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, self.NOTE_FIELDS)
        self._validate_note_types(resp.data)

    def test_update_note_response_shape(self):
        resp = self.api.patch(
            f"/api/v1/encounters/{self.encounter.id}/note/",
            {"subjective": "Updated subjective."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, self.NOTE_FIELDS)
        self.assertEqual(resp.data["subjective"], "Updated subjective.")

    def test_approve_note_response_shape(self):
        resp = self.api.post(f"/api/v1/encounters/{self.encounter.id}/note/approve/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, self.NOTE_FIELDS)
        self.assertIsNotNone(resp.data["approved_at"])
        self.assertTrue(_iso_datetime(resp.data["approved_at"]))
        self.assertIsNotNone(resp.data["approved_by"])

    def test_get_note_404_when_missing(self):
        enc2 = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        resp = self.api.get(f"/api/v1/encounters/{enc2.id}/note/")
        self.assertEqual(resp.status_code, 404)

    # -- helpers --
    def _validate_note_types(self, data):
        self.assertTrue(_uuid_str(data["id"]))
        self.assertTrue(_uuid_str(data["encounter"]))
        self.assertIn(data["note_type"], self.NOTE_TYPES)
        self.assertIsInstance(data["subjective"], str)
        self.assertIsInstance(data["objective"], str)
        self.assertIsInstance(data["assessment"], str)
        self.assertIsInstance(data["plan"], str)
        self.assertIsInstance(data["raw_content"], str)
        self.assertIsInstance(data["icd10_codes"], list)
        self.assertIsInstance(data["cpt_codes"], list)
        self.assertIsInstance(data["ai_generated"], bool)
        self.assertIsInstance(data["doctor_edited"], bool)
        self.assertTrue(_iso_datetime(data["approved_at"]))
        self.assertTrue(_iso_datetime(data["created_at"]))
        self.assertTrue(_iso_datetime(data["updated_at"]))
        # prompt_version_detail is object or None
        pv = data["prompt_version_detail"]
        if pv is not None:
            _assert_keys(self, pv, ["id", "prompt_name", "version", "is_active", "created_at"])


# ===========================================================================
# 6. SUMMARY CONTRACTS (Doctor-facing)
# ===========================================================================

class DoctorSummaryContractTests(BaseContractTest):
    """
    Validates:
      GET  /api/v1/encounters/:id/summary/      -> PatientSummary
      POST /api/v1/encounters/:id/summary/send/  -> PatientSummary
    """

    SUMMARY_FIELDS = [
        "id", "encounter", "clinical_note", "summary_en", "summary_es",
        "reading_level", "medical_terms_explained", "disclaimer_text",
        "delivery_status", "delivered_at", "viewed_at", "delivery_method",
        "prompt_version", "created_at", "updated_at",
    ]
    READING_LEVELS = ["grade_5", "grade_8", "grade_12"]
    DELIVERY_STATUSES = ["pending", "sent", "viewed", "failed"]

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
            summary_en="English summary.",
            summary_es="Resumen en espanol.",
            reading_level="grade_8",
            medical_terms_explained=[
                {"term": "hypertension", "explanation": "high blood pressure"}
            ],
            delivery_status="pending",
        )

    def test_get_summary_response_shape(self):
        resp = self.api.get(f"/api/v1/encounters/{self.encounter.id}/summary/")
        self.assertEqual(resp.status_code, 200)
        self._validate_summary(resp.data)

    def test_send_summary_response_shape(self):
        resp = self.api.post(
            f"/api/v1/encounters/{self.encounter.id}/summary/send/",
            {"delivery_method": "app"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self._validate_summary(resp.data)
        self.assertEqual(resp.data["delivery_status"], "sent")
        self.assertIsNotNone(resp.data["delivered_at"])

    def test_get_summary_404_when_missing(self):
        enc2 = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        resp = self.api.get(f"/api/v1/encounters/{enc2.id}/summary/")
        self.assertEqual(resp.status_code, 404)

    def _validate_summary(self, data):
        _assert_keys(self, data, self.SUMMARY_FIELDS)
        self.assertTrue(_uuid_str(data["id"]))
        self.assertTrue(_uuid_str(data["encounter"]))
        self.assertTrue(_uuid_str(data["clinical_note"]))
        self.assertIsInstance(data["summary_en"], str)
        self.assertIsInstance(data["summary_es"], str)
        self.assertIn(data["reading_level"], self.READING_LEVELS)
        self.assertIsInstance(data["medical_terms_explained"], list)
        if data["medical_terms_explained"]:
            term = data["medical_terms_explained"][0]
            _assert_keys(self, term, ["term", "explanation"])
            self.assertIsInstance(term["term"], str)
            self.assertIsInstance(term["explanation"], str)
        self.assertIsInstance(data["disclaimer_text"], str)
        self.assertIn(data["delivery_status"], self.DELIVERY_STATUSES)
        self.assertTrue(_iso_datetime(data["delivered_at"]))
        self.assertTrue(_iso_datetime(data["viewed_at"]))
        self.assertIsInstance(data["delivery_method"], str)
        self.assertTrue(_iso_datetime(data["created_at"]))
        self.assertTrue(_iso_datetime(data["updated_at"]))


# ===========================================================================
# 7. PATIENT-FACING SUMMARY CONTRACTS (mobile app)
# ===========================================================================

class PatientSummaryContractTests(BaseContractTest):
    """
    Validates mobile API contract:
      GET   /api/v1/patient/summaries/              -> PatientSummaryListResponse
      GET   /api/v1/patient/summaries/:id/          -> PatientSummary (patient-facing)
      PATCH /api/v1/patient/summaries/:id/read/     -> {status: "viewed"}
    """

    PATIENT_SUMMARY_FIELDS = [
        "id", "summary_en", "summary_es", "reading_level",
        "medical_terms_explained", "disclaimer_text",
        "encounter_date", "doctor_name", "delivery_status",
        "viewed_at", "created_at",
    ]

    def setUp(self):
        super().setUp()
        # Create a patient user matching the patient record phone
        self.patient_user = User.objects.create_user(
            email="+15559990000@patient.medicalnote.local",
            role="patient",
            phone="+15559990000",
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
            summary_en="Your visit summary.",
            summary_es="Resumen de su visita.",
            reading_level="grade_8",
            medical_terms_explained=[],
            delivery_status="sent",
        )
        self.api.force_authenticate(user=self.patient_user)

    def test_patient_summary_list_response_shape(self):
        resp = self.api.get("/api/v1/patient/summaries/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, ["count", "results"])
        self.assertIsInstance(resp.data["count"], int)
        self.assertIsInstance(resp.data["results"], list)
        self.assertGreater(len(resp.data["results"]), 0)
        item = resp.data["results"][0]
        _assert_keys(self, item, self.PATIENT_SUMMARY_FIELDS)
        self._validate_patient_summary(item)

    def test_patient_summary_detail_response_shape(self):
        resp = self.api.get(f"/api/v1/patient/summaries/{self.summary.id}/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, self.PATIENT_SUMMARY_FIELDS)
        self._validate_patient_summary(resp.data)

    def test_patient_mark_read_response_shape(self):
        resp = self.api.patch(f"/api/v1/patient/summaries/{self.summary.id}/read/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, ["status"])
        self.assertEqual(resp.data["status"], "viewed")

    def test_patient_summary_list_excludes_pending(self):
        """Pending summaries should not appear in patient view."""
        self.summary.delivery_status = "pending"
        self.summary.save(update_fields=["delivery_status"])
        resp = self.api.get("/api/v1/patient/summaries/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 0)

    def _validate_patient_summary(self, data):
        self.assertTrue(_uuid_str(data["id"]))
        self.assertIsInstance(data["summary_en"], str)
        self.assertIsInstance(data["summary_es"], str)
        self.assertIn(data["reading_level"], ["grade_5", "grade_8", "grade_12"])
        self.assertIsInstance(data["medical_terms_explained"], list)
        self.assertIsInstance(data["disclaimer_text"], str)
        self.assertTrue(_iso_date(data["encounter_date"]))
        self.assertIsInstance(data["doctor_name"], str)
        self.assertIn(data["delivery_status"], ["pending", "sent", "viewed", "failed"])
        self.assertTrue(_iso_datetime(data["viewed_at"]))
        self.assertTrue(_iso_datetime(data["created_at"]))


# ===========================================================================
# 8. WIDGET CONTRACTS
# ===========================================================================

class WidgetContractTests(BaseContractTest):
    """
    Validates:
      GET  /api/v1/widget/config/:widget_key/ -> WidgetBrandConfig
      GET  /api/v1/widget/summary/:token/     -> WidgetSummaryData
      POST /api/v1/widget/summary/:token/read/ -> {status: "viewed"}
    """

    WIDGET_CONFIG_FIELDS = [
        "practice_name", "widget_key",
    ]
    WIDGET_SUMMARY_FIELDS = [
        "id", "summary_en", "summary_es", "reading_level",
        "medical_terms_explained", "disclaimer_text",
        "encounter_date", "doctor_name", "delivery_status",
        "viewed_at", "created_at",
    ]

    def setUp(self):
        super().setUp()
        # Set up white-label config with widget_key
        self.practice.white_label_config = {
            "widget_key": "test-widget-key-123",
            "logo_url": "https://example.com/logo.png",
            "brand_color": "#1a73e8",
            "custom_domain": "clinic.example.com",
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
            summary_en="Widget summary EN.",
            summary_es="Widget summary ES.",
            reading_level="grade_5",
            delivery_status="sent",
        )

    def test_widget_config_response_shape(self):
        client = APIClient()  # No auth needed
        resp = client.get("/api/v1/widget/config/test-widget-key-123/")
        self.assertEqual(resp.status_code, 200, resp.data)
        _assert_keys(self, resp.data, self.WIDGET_CONFIG_FIELDS)
        self.assertIsInstance(resp.data["practice_name"], str)
        self.assertEqual(resp.data["widget_key"], "test-widget-key-123")
        # Optional branding fields
        self.assertIn("logo_url", resp.data)
        self.assertIn("brand_color", resp.data)

    def test_widget_config_404_invalid_key(self):
        client = APIClient()
        resp = client.get("/api/v1/widget/config/invalid-key/")
        self.assertEqual(resp.status_code, 404)
        _assert_keys(self, resp.data, ["error"])

    def test_widget_summary_response_shape(self):
        signer = TimestampSigner()
        token = signer.sign(str(self.summary.id))
        client = APIClient()
        resp = client.get(f"/api/v1/widget/summary/{token}/")
        self.assertEqual(resp.status_code, 200, resp.data)
        _assert_keys(self, resp.data, self.WIDGET_SUMMARY_FIELDS)
        self.assertTrue(_uuid_str(resp.data["id"]))
        self.assertIsInstance(resp.data["summary_en"], str)
        self.assertIsInstance(resp.data["doctor_name"], str)
        self.assertTrue(_iso_date(resp.data["encounter_date"]))

    def test_widget_summary_invalid_token_returns_403(self):
        client = APIClient()
        resp = client.get("/api/v1/widget/summary/invalid-token/")
        self.assertEqual(resp.status_code, 403)
        _assert_keys(self, resp.data, ["error"])

    def test_widget_mark_read_response_shape(self):
        signer = TimestampSigner()
        token = signer.sign(str(self.summary.id))
        client = APIClient()
        resp = client.post(f"/api/v1/widget/summary/{token}/read/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, ["status"])
        self.assertEqual(resp.data["status"], "viewed")

    def test_widget_mark_read_invalid_token_returns_403(self):
        client = APIClient()
        resp = client.post("/api/v1/widget/summary/bad-token/read/")
        self.assertEqual(resp.status_code, 403)


# ===========================================================================
# 9. PRACTICE CONTRACTS
# ===========================================================================

class PracticeContractTests(BaseContractTest):
    """
    Validates:
      GET   /api/v1/practice/       -> Practice
      PATCH /api/v1/practice/       -> Practice
      GET   /api/v1/practice/stats/ -> PracticeStats
    """

    PRACTICE_FIELDS = [
        "id", "name", "address", "phone", "subscription_tier",
        "white_label_config", "created_at", "updated_at",
    ]

    def test_get_practice_response_shape(self):
        resp = self.api.get("/api/v1/practice/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, self.PRACTICE_FIELDS)
        self.assertTrue(_uuid_str(resp.data["id"]))
        self.assertIn(resp.data["subscription_tier"], ["solo", "group", "enterprise"])
        self.assertTrue(_iso_datetime(resp.data["created_at"]))

    def test_update_practice_response_shape(self):
        resp = self.api.patch("/api/v1/practice/", {
            "name": "Updated Clinic Name",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, self.PRACTICE_FIELDS)
        self.assertEqual(resp.data["name"], "Updated Clinic Name")

    def test_practice_stats_response_shape(self):
        resp = self.api.get("/api/v1/practice/stats/")
        self.assertEqual(resp.status_code, 200)
        _assert_keys(self, resp.data, [
            "total_patients", "total_encounters", "encounters_by_status",
        ])
        self.assertIsInstance(resp.data["total_patients"], int)
        self.assertIsInstance(resp.data["total_encounters"], int)
        self.assertIsInstance(resp.data["encounters_by_status"], dict)


# ===========================================================================
# 10. CROSS-CUTTING CONCERNS
# ===========================================================================

class AuthorizationContractTests(BaseContractTest):
    """Verify that unauthenticated and wrong-role requests get proper errors."""

    def test_unauthenticated_patient_list_returns_401_or_403(self):
        client = APIClient()
        resp = client.get("/api/v1/patients/")
        self.assertIn(resp.status_code, [401, 403])

    def test_patient_role_cannot_access_doctor_endpoints(self):
        patient_user = User.objects.create_user(
            email="wrong_role@test.com",
            role="patient",
        )
        self.api.force_authenticate(user=patient_user)
        resp = self.api.get("/api/v1/patients/")
        self.assertEqual(resp.status_code, 403)

    def test_doctor_cannot_access_patient_summaries_endpoint(self):
        resp = self.api.get("/api/v1/patient/summaries/")
        self.assertEqual(resp.status_code, 403)
