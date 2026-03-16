"""
End-to-End Pipeline Tests
==========================
Test the complete recording pipeline with mocked external services.

These tests simulate the full user journey:
  1. Doctor registers and logs in
  2. Doctor creates a patient
  3. Doctor creates an encounter with paste input
  4. Celery workers process (mock Claude and AWS APIs)
  5. Verify transcript, SOAP note, and summary are created
  6. Doctor reviews and approves the note
  7. Doctor sends summary to patient
  8. Patient logs in via OTP
  9. Patient views their summaries
  10. Patient marks summary as read
  11. Verify all audit logs were created

All external services (Claude API, AWS HealthScribe, Textract, S3, Twilio)
are mocked.
"""

from datetime import date
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.core.signing import TimestampSigner
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Practice, User
from apps.audit.models import AuditLog
from apps.encounters.models import Encounter, Recording, Transcript
from apps.notes.models import ClinicalNote, PromptVersion
from apps.patients.models import Patient
from apps.summaries.models import PatientSummary


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION="none",
)
class FullDoctorPatientPipelineTest(TestCase):
    """
    Complete end-to-end pipeline: doctor registers, creates patient, creates
    encounter with paste, workers generate note + summary, doctor approves
    and sends, patient logs in via OTP and views summary.
    """

    def setUp(self):
        self.client = APIClient()
        # Seed prompt versions required by workers
        PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="Generate a SOAP note from: {transcript}",
            is_active=True,
        )
        PromptVersion.objects.create(
            prompt_name="patient_summary",
            version="1.0.0",
            template_text="Generate a summary from: {note}",
            is_active=True,
        )

    @patch("workers.summary.LLMService")
    @patch("workers.soap_note.LLMService")
    @patch("services.notification_service.NotificationService")
    def test_full_pipeline_paste_flow(
        self, mock_sms_cls, mock_soap_llm_cls, mock_summary_llm_cls
    ):
        # ---------------------------------------------------------------
        # Configure mocks
        # ---------------------------------------------------------------
        mock_sms = MagicMock()
        mock_sms_cls.return_value = mock_sms

        mock_soap_llm = MagicMock()
        mock_soap_llm_cls.return_value = mock_soap_llm
        mock_soap_llm.generate_soap_note.return_value = {
            "subjective": "Patient presents with a persistent cough for 5 days. No fever or shortness of breath.",
            "objective": "Temp 98.6F, BP 118/76, HR 72. Lungs clear bilaterally. Throat mildly erythematous.",
            "assessment": "Acute upper respiratory infection, likely viral.",
            "plan": "Supportive care: rest, fluids, OTC cough suppressant. Follow up if symptoms worsen or persist beyond 10 days.",
            "icd10_codes": ["J06.9"],
            "cpt_codes": ["99213"],
        }

        mock_summary_llm = MagicMock()
        mock_summary_llm_cls.return_value = mock_summary_llm
        mock_summary_llm.generate_patient_summary.return_value = {
            "summary_en": (
                "You visited the doctor today because of a cough that has lasted 5 days. "
                "Your temperature and blood pressure are normal. The doctor thinks you have "
                "a common cold. You should rest, drink plenty of fluids, and take cough "
                "medicine from the store. Come back if you feel worse or the cough lasts "
                "more than 10 days."
            ),
            "summary_es": (
                "Usted visito al medico hoy por una tos que ha durado 5 dias. "
                "Su temperatura y presion arterial son normales. El medico piensa que usted "
                "tiene un resfriado comun. Debe descansar, tomar muchos liquidos y tomar "
                "medicamentos para la tos de la tienda."
            ),
            "medical_terms_explained": [
                {
                    "term": "upper respiratory infection",
                    "explanation": "a common cold or infection of the nose, throat, and airways",
                },
                {
                    "term": "erythematous",
                    "explanation": "red and inflamed",
                },
            ],
        }

        # ---------------------------------------------------------------
        # Step 1: Doctor registers
        # ---------------------------------------------------------------
        reg_resp = self.client.post("/api/v1/auth/registration/", {
            "email": "pipeline_doc@test.com",
            "password1": "Str0ngP@ssw0rd!",
            "password2": "Str0ngP@ssw0rd!",
            "first_name": "Pipeline",
            "last_name": "Doctor",
            "practice_name": "Pipeline Clinic",
        }, format="json")
        self.assertEqual(reg_resp.status_code, 201, reg_resp.data)
        doctor_access = reg_resp.data["access"]
        doctor_user_data = reg_resp.data["user"]
        self.assertEqual(doctor_user_data["role"], "doctor")
        self.assertEqual(doctor_user_data["practice_name"], "Pipeline Clinic")

        # ---------------------------------------------------------------
        # Step 2: Doctor logs in (verify login also works)
        # ---------------------------------------------------------------
        login_resp = self.client.post("/api/v1/auth/login/", {
            "email": "pipeline_doc@test.com",
            "password": "Str0ngP@ssw0rd!",
        }, format="json")
        self.assertEqual(login_resp.status_code, 200)
        doctor_access = login_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {doctor_access}")

        # Verify GET /auth/user/ returns correct user
        user_resp = self.client.get("/api/v1/auth/user/")
        self.assertEqual(user_resp.status_code, 200)
        self.assertEqual(user_resp.data["email"], "pipeline_doc@test.com")
        self.assertEqual(user_resp.data["first_name"], "Pipeline")
        self.assertEqual(user_resp.data["last_name"], "Doctor")

        # ---------------------------------------------------------------
        # Step 3: Doctor creates a patient
        # ---------------------------------------------------------------
        patient_resp = self.client.post("/api/v1/patients/", {
            "first_name": "Pipeline",
            "last_name": "Patient",
            "date_of_birth": "1988-07-22",
            "phone": "+15558881234",
            "email": "pipelinepat@test.com",
        }, format="json")
        self.assertEqual(patient_resp.status_code, 201, patient_resp.data)
        patient_id = patient_resp.data["id"]
        self.assertIsNotNone(patient_id)
        self.assertEqual(patient_resp.data["first_name"], "Pipeline")

        # Verify patient appears in list
        list_resp = self.client.get("/api/v1/patients/")
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.data["count"], 1)

        # ---------------------------------------------------------------
        # Step 4: Doctor creates an encounter with paste input
        # ---------------------------------------------------------------
        encounter_resp = self.client.post("/api/v1/encounters/", {
            "patient": patient_id,
            "encounter_date": "2026-03-15",
            "input_method": "paste",
            "consent_recording": True,
            "consent_method": "verbal",
        }, format="json")
        self.assertEqual(encounter_resp.status_code, 201, encounter_resp.data)
        encounter_id = encounter_resp.data["id"]
        self.assertEqual(encounter_resp.data["input_method"], "paste")
        self.assertEqual(encounter_resp.data["status"], "uploading")

        # ---------------------------------------------------------------
        # Step 5: Doctor pastes clinical text (triggers workers synchronously)
        # ---------------------------------------------------------------
        paste_text = (
            "Patient is a 36-year-old male presenting with a persistent cough "
            "for 5 days. No fever, no shortness of breath. No recent travel. "
            "Vitals: Temp 98.6F, BP 118/76, HR 72. Lungs clear bilaterally. "
            "Throat mildly erythematous. Assessment: Acute URI, likely viral."
        )
        paste_resp = self.client.post(
            f"/api/v1/encounters/{encounter_id}/paste/",
            {"text": paste_text},
            format="json",
        )
        self.assertEqual(paste_resp.status_code, 202, paste_resp.data)
        self.assertEqual(paste_resp.data["status"], "processing")
        self.assertEqual(paste_resp.data["encounter_id"], encounter_id)

        # ---------------------------------------------------------------
        # Step 6: Verify transcript was created from paste
        # ---------------------------------------------------------------
        transcript_resp = self.client.get(f"/api/v1/encounters/{encounter_id}/transcript/")
        self.assertEqual(transcript_resp.status_code, 200)
        self.assertEqual(transcript_resp.data["raw_text"], paste_text)
        self.assertEqual(transcript_resp.data["confidence_score"], 1.0)

        # ---------------------------------------------------------------
        # Step 7: Verify SOAP note was generated
        # ---------------------------------------------------------------
        encounter = Encounter.objects.get(id=encounter_id)
        self.assertEqual(encounter.status, "ready_for_review")

        note_resp = self.client.get(f"/api/v1/encounters/{encounter_id}/note/")
        self.assertEqual(note_resp.status_code, 200)
        self.assertEqual(note_resp.data["note_type"], "soap")
        self.assertIn("persistent cough", note_resp.data["subjective"])
        self.assertIn("Temp 98.6F", note_resp.data["objective"])
        self.assertEqual(note_resp.data["ai_generated"], True)
        self.assertEqual(note_resp.data["doctor_edited"], False)
        self.assertIsNone(note_resp.data["approved_at"])
        self.assertEqual(note_resp.data["icd10_codes"], ["J06.9"])
        self.assertEqual(note_resp.data["cpt_codes"], ["99213"])

        # Verify SOAP note worker was called with correct arguments
        mock_soap_llm.generate_soap_note.assert_called_once()
        call_args = mock_soap_llm.generate_soap_note.call_args
        self.assertEqual(call_args[0][0], paste_text)  # transcript text

        # ---------------------------------------------------------------
        # Step 8: Verify summary was generated
        # ---------------------------------------------------------------
        summary_resp = self.client.get(f"/api/v1/encounters/{encounter_id}/summary/")
        self.assertEqual(summary_resp.status_code, 200)
        self.assertIn("cough", summary_resp.data["summary_en"])
        self.assertEqual(summary_resp.data["reading_level"], "grade_8")
        self.assertEqual(summary_resp.data["delivery_status"], "pending")
        self.assertEqual(len(summary_resp.data["medical_terms_explained"]), 2)
        self.assertIsNotNone(summary_resp.data["disclaimer_text"])

        # Verify summary worker was called with SOAP note sections
        mock_summary_llm.generate_patient_summary.assert_called_once()

        # ---------------------------------------------------------------
        # Step 9: Doctor edits the note
        # ---------------------------------------------------------------
        edit_resp = self.client.patch(
            f"/api/v1/encounters/{encounter_id}/note/",
            {
                "plan": "Rest, fluids, OTC cough suppressant. RTC in 10 days if not improved. Consider CXR if worsening.",
                "doctor_edited": True,
            },
            format="json",
        )
        self.assertEqual(edit_resp.status_code, 200)
        self.assertTrue(edit_resp.data["doctor_edited"])
        self.assertIn("CXR", edit_resp.data["plan"])

        # ---------------------------------------------------------------
        # Step 10: Doctor approves the note
        # ---------------------------------------------------------------
        approve_resp = self.client.post(f"/api/v1/encounters/{encounter_id}/note/approve/")
        self.assertEqual(approve_resp.status_code, 200)
        self.assertIsNotNone(approve_resp.data["approved_at"])
        self.assertIsNotNone(approve_resp.data["approved_by"])

        encounter.refresh_from_db()
        self.assertEqual(encounter.status, "approved")

        # ---------------------------------------------------------------
        # Step 11: Doctor sends summary to patient
        # ---------------------------------------------------------------
        send_resp = self.client.post(
            f"/api/v1/encounters/{encounter_id}/summary/send/",
            {"delivery_method": "app"},
            format="json",
        )
        self.assertEqual(send_resp.status_code, 200)
        self.assertEqual(send_resp.data["delivery_status"], "sent")
        self.assertIsNotNone(send_resp.data["delivered_at"])
        self.assertEqual(send_resp.data["delivery_method"], "app")

        encounter.refresh_from_db()
        self.assertEqual(encounter.status, "delivered")

        # ---------------------------------------------------------------
        # Step 12: Verify encounter detail shows all artifacts
        # ---------------------------------------------------------------
        detail_resp = self.client.get(f"/api/v1/encounters/{encounter_id}/")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertTrue(detail_resp.data["has_transcript"])
        self.assertTrue(detail_resp.data["has_note"])
        self.assertTrue(detail_resp.data["has_summary"])

        # ---------------------------------------------------------------
        # Step 13: Patient logs in via OTP
        # ---------------------------------------------------------------
        patient_phone = "+15558881234"
        # Simulate OTP send
        cache.set(f"otp:{patient_phone}", "111222", timeout=300)
        cache.set(f"otp_attempts:{patient_phone}", 0, timeout=300)

        otp_client = APIClient()
        otp_resp = otp_client.post("/api/v1/auth/patient/otp/verify/", {
            "phone": patient_phone,
            "code": "111222",
        }, format="json")
        self.assertEqual(otp_resp.status_code, 200, otp_resp.data)
        patient_access = otp_resp.data["access"]
        patient_user_id = otp_resp.data["user_id"]

        # ---------------------------------------------------------------
        # Step 14: Patient views their summaries
        # ---------------------------------------------------------------
        patient_client = APIClient()
        patient_client.credentials(HTTP_AUTHORIZATION=f"Bearer {patient_access}")

        summaries_resp = patient_client.get("/api/v1/patient/summaries/")
        self.assertEqual(summaries_resp.status_code, 200)
        self.assertEqual(summaries_resp.data["count"], 1)

        patient_summary = summaries_resp.data["results"][0]
        summary_id = patient_summary["id"]
        self.assertIn("cough", patient_summary["summary_en"])
        self.assertIn("Dr.", patient_summary["doctor_name"])
        self.assertEqual(patient_summary["delivery_status"], "sent")

        # ---------------------------------------------------------------
        # Step 15: Patient views detail
        # ---------------------------------------------------------------
        detail_resp = patient_client.get(f"/api/v1/patient/summaries/{summary_id}/")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(detail_resp.data["id"], summary_id)

        # ---------------------------------------------------------------
        # Step 16: Patient marks summary as read
        # ---------------------------------------------------------------
        read_resp = patient_client.patch(f"/api/v1/patient/summaries/{summary_id}/read/")
        self.assertEqual(read_resp.status_code, 200)
        self.assertEqual(read_resp.data["status"], "viewed")

        # Verify in database
        db_summary = PatientSummary.objects.get(id=summary_id)
        self.assertEqual(db_summary.delivery_status, "viewed")
        self.assertIsNotNone(db_summary.viewed_at)

        # ---------------------------------------------------------------
        # Step 17: Verify audit logs were created
        # ---------------------------------------------------------------
        audit_logs = AuditLog.objects.filter(user__email="pipeline_doc@test.com")
        audit_actions = set(audit_logs.values_list("action", flat=True))
        audit_resources = set(audit_logs.values_list("resource_type", flat=True))

        # Doctor should have created audit entries for patient, encounter, note, summary
        self.assertIn("patient", audit_resources)
        self.assertIn("encounter", audit_resources)

        # All audit logs should have PHI flag and IP address
        for log in audit_logs:
            self.assertTrue(log.phi_accessed)
            self.assertIsNotNone(log.ip_address)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION="none",
)
class WidgetPipelineTest(TestCase):
    """
    Test the widget flow: doctor sends summary via widget, anonymous user
    views it via signed token.
    """

    def setUp(self):
        self.practice = Practice.objects.create(
            name="Widget Pipeline Clinic",
            subscription_tier="group",
            white_label_config={
                "widget_key": "widget-pipeline-key",
                "logo_url": "https://example.com/logo.png",
                "brand_color": "#4caf50",
                "custom_domain": "widget.example.com",
            },
        )
        self.doctor = User.objects.create_user(
            email="widget_doc@test.com",
            password="WidgetP@ss1!",
            role="doctor",
            first_name="Widget",
            last_name="Doctor",
            practice=self.practice,
        )
        self.patient_record = Patient.objects.create(
            practice=self.practice,
            first_name="Widget",
            last_name="Patient",
            date_of_birth=date(1975, 11, 3),
            phone="+15557770000",
        )
        PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="p",
            is_active=True,
        )
        PromptVersion.objects.create(
            prompt_name="patient_summary",
            version="1.0.0",
            template_text="p",
            is_active=True,
        )

    @patch("workers.summary.LLMService")
    @patch("workers.soap_note.LLMService")
    def test_widget_flow_end_to_end(self, mock_soap_cls, mock_summary_cls):
        mock_soap = MagicMock()
        mock_soap_cls.return_value = mock_soap
        mock_soap.generate_soap_note.return_value = {
            "subjective": "Knee pain for 2 weeks",
            "objective": "Swelling noted on right knee",
            "assessment": "Possible meniscus tear",
            "plan": "MRI recommended, ice and rest",
            "icd10_codes": ["M23.30"],
            "cpt_codes": ["99214"],
        }

        mock_summary = MagicMock()
        mock_summary_cls.return_value = mock_summary
        mock_summary.generate_patient_summary.return_value = {
            "summary_en": "You visited the doctor for knee pain.",
            "summary_es": "Usted visito al medico por dolor de rodilla.",
            "medical_terms_explained": [
                {"term": "meniscus tear", "explanation": "a torn piece of cartilage in the knee"},
            ],
        }

        doctor_client = APIClient()
        doctor_client.force_authenticate(user=self.doctor)

        # Create encounter and paste
        enc_resp = doctor_client.post("/api/v1/encounters/", {
            "patient": str(self.patient_record.id),
            "encounter_date": "2026-03-15",
            "input_method": "paste",
        }, format="json")
        encounter_id = enc_resp.data["id"]

        paste_resp = doctor_client.post(
            f"/api/v1/encounters/{encounter_id}/paste/",
            {"text": "Patient presents with right knee pain for 2 weeks. Swelling noted. Assessment: possible meniscus tear."},
            format="json",
        )
        self.assertEqual(paste_resp.status_code, 202)

        # Approve note
        doctor_client.post(f"/api/v1/encounters/{encounter_id}/note/approve/")

        # Send via widget
        send_resp = doctor_client.post(
            f"/api/v1/encounters/{encounter_id}/summary/send/",
            {"delivery_method": "widget"},
            format="json",
        )
        self.assertEqual(send_resp.status_code, 200)
        self.assertEqual(send_resp.data["delivery_method"], "widget")
        summary_id = send_resp.data["id"]

        # ---------------------------------------------------------------
        # Widget client (anonymous) fetches config
        # ---------------------------------------------------------------
        anon_client = APIClient()
        config_resp = anon_client.get("/api/v1/widget/config/widget-pipeline-key/")
        self.assertEqual(config_resp.status_code, 200)
        self.assertEqual(config_resp.data["practice_name"], "Widget Pipeline Clinic")
        self.assertEqual(config_resp.data["brand_color"], "#4caf50")

        # ---------------------------------------------------------------
        # Widget client fetches summary via signed token
        # ---------------------------------------------------------------
        signer = TimestampSigner()
        token = signer.sign(str(summary_id))

        summary_resp = anon_client.get(f"/api/v1/widget/summary/{token}/")
        self.assertEqual(summary_resp.status_code, 200)
        self.assertIn("knee pain", summary_resp.data["summary_en"])
        self.assertIn("Dr.", summary_resp.data["doctor_name"])
        self.assertEqual(summary_resp.data["delivery_status"], "sent")

        # ---------------------------------------------------------------
        # Widget client marks summary as read
        # ---------------------------------------------------------------
        read_resp = anon_client.post(f"/api/v1/widget/summary/{token}/read/")
        self.assertEqual(read_resp.status_code, 200)
        self.assertEqual(read_resp.data["status"], "viewed")

        # Verify in database
        db_summary = PatientSummary.objects.get(id=summary_id)
        self.assertEqual(db_summary.delivery_status, "viewed")
        self.assertIsNotNone(db_summary.viewed_at)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION="none",
)
class DictationFlowTest(TestCase):
    """Test the dictation input method pipeline."""

    def setUp(self):
        self.practice = Practice.objects.create(
            name="Dictation Clinic",
            subscription_tier="solo",
        )
        self.doctor = User.objects.create_user(
            email="dictation_doc@test.com",
            password="DictP@ssw0rd!",
            role="doctor",
            first_name="Dict",
            last_name="Doc",
            practice=self.practice,
        )
        self.patient_record = Patient.objects.create(
            practice=self.practice,
            first_name="Dict",
            last_name="Patient",
            date_of_birth=date(1995, 3, 20),
        )
        PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="p",
            is_active=True,
        )
        PromptVersion.objects.create(
            prompt_name="patient_summary",
            version="1.0.0",
            template_text="p",
            is_active=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.doctor)

    @patch("workers.summary.LLMService")
    @patch("workers.soap_note.LLMService")
    def test_dictation_creates_transcript_and_note(self, mock_soap_cls, mock_summary_cls):
        mock_soap = MagicMock()
        mock_soap_cls.return_value = mock_soap
        mock_soap.generate_soap_note.return_value = {
            "subjective": "Dictated subjective",
            "objective": "Dictated objective",
            "assessment": "Dictated assessment",
            "plan": "Dictated plan",
            "icd10_codes": [],
            "cpt_codes": [],
        }
        mock_summary = MagicMock()
        mock_summary_cls.return_value = mock_summary
        mock_summary.generate_patient_summary.return_value = {
            "summary_en": "Dictation summary.",
            "summary_es": "Resumen de dictado.",
            "medical_terms_explained": [],
        }

        enc_resp = self.api.post("/api/v1/encounters/", {
            "patient": str(self.patient_record.id),
            "encounter_date": "2026-03-15",
            "input_method": "dictation",
        }, format="json")
        encounter_id = enc_resp.data["id"]

        dict_resp = self.api.post(
            f"/api/v1/encounters/{encounter_id}/dictation/",
            {"text": "The patient is a 30-year-old female with ongoing migraines. Frequency two per week."},
            format="json",
        )
        self.assertEqual(dict_resp.status_code, 202)
        self.assertEqual(dict_resp.data["status"], "processing")

        # Verify pipeline completed
        encounter = Encounter.objects.get(id=encounter_id)
        self.assertEqual(encounter.status, "ready_for_review")

        transcript = Transcript.objects.get(encounter=encounter)
        self.assertIn("migraines", transcript.raw_text)

        note = ClinicalNote.objects.get(encounter=encounter)
        self.assertTrue(note.ai_generated)

        summary = PatientSummary.objects.get(encounter=encounter)
        self.assertIn("Dictation summary", summary.summary_en)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION="none",
)
class TokenRefreshFlowTest(TestCase):
    """Test the token refresh flow used by all three frontends."""

    def test_access_token_refresh_cycle(self):
        """Simulate the refresh flow: login -> use access -> refresh -> use new access."""
        from unittest.mock import patch as _patch
        from dj_rest_auth.app_settings import api_settings

        practice = Practice.objects.create(name="Refresh Clinic", subscription_tier="solo")
        User.objects.create_user(
            email="refresh_doc@test.com",
            password="Ref@shP@ss1!",
            role="doctor",
            first_name="Refresh",
            last_name="Doc",
            practice=practice,
        )

        with _patch.object(api_settings, "JWT_AUTH_HTTPONLY", False):
            client = APIClient()

            # Login
            login_resp = client.post("/api/v1/auth/login/", {
                "email": "refresh_doc@test.com",
                "password": "Ref@shP@ss1!",
            }, format="json")
            self.assertEqual(login_resp.status_code, 200)
            access_1 = login_resp.data["access"]
            refresh_1 = login_resp.data["refresh"]

            # Use access token
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_1}")
            user_resp = client.get("/api/v1/auth/user/")
            self.assertEqual(user_resp.status_code, 200)

            # Refresh the token
            client.credentials()  # Clear auth
            refresh_resp = client.post("/api/v1/auth/token/refresh/", {
                "refresh": refresh_1,
            }, format="json")
            self.assertEqual(refresh_resp.status_code, 200)
            access_2 = refresh_resp.data["access"]
            refresh_2 = refresh_resp.data["refresh"]

            # New tokens are different
            self.assertNotEqual(access_1, access_2)

            # Use new access token
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_2}")
            user_resp2 = client.get("/api/v1/auth/user/")
            self.assertEqual(user_resp2.status_code, 200)
            self.assertEqual(user_resp2.data["email"], "refresh_doc@test.com")


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=False,
    ACCOUNT_EMAIL_VERIFICATION="none",
)
class WorkerFailureHandlingTest(TestCase):
    """Test that worker failures are handled gracefully and encounter status is updated."""

    def setUp(self):
        self.practice = Practice.objects.create(
            name="Failure Test Clinic",
            subscription_tier="solo",
        )
        self.doctor = User.objects.create_user(
            email="failure_doc@test.com",
            password="F@ilP@ss1!",
            role="doctor",
            first_name="Fail",
            last_name="Doc",
            practice=self.practice,
        )
        self.patient_record = Patient.objects.create(
            practice=self.practice,
            first_name="Fail",
            last_name="Patient",
            date_of_birth=date(1980, 5, 10),
        )
        PromptVersion.objects.create(
            prompt_name="soap_note",
            version="1.0.0",
            template_text="p",
            is_active=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.doctor)

    @patch("workers.soap_note.LLMService")
    def test_soap_note_failure_sets_encounter_status(self, mock_llm_cls):
        """When SOAP note generation fails, encounter status becomes note_generation_failed."""
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.generate_soap_note.side_effect = Exception("Claude API timeout")

        enc_resp = self.api.post("/api/v1/encounters/", {
            "patient": str(self.patient_record.id),
            "encounter_date": "2026-03-15",
            "input_method": "paste",
        }, format="json")
        encounter_id = enc_resp.data["id"]

        # Paste triggers the SOAP note task which will fail
        paste_resp = self.api.post(
            f"/api/v1/encounters/{encounter_id}/paste/",
            {"text": "Patient presents with severe abdominal pain. Onset 2 hours ago."},
            format="json",
        )
        self.assertEqual(paste_resp.status_code, 202)

        # Verify encounter status reflects the failure
        encounter = Encounter.objects.get(id=encounter_id)
        self.assertEqual(encounter.status, "note_generation_failed")

        # Note endpoint should return 404 since note was never created
        note_resp = self.api.get(f"/api/v1/encounters/{encounter_id}/note/")
        self.assertEqual(note_resp.status_code, 404)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION="none",
)
class MultiPracticeIsolationTest(TestCase):
    """Verify that data is isolated between practices (multi-tenancy)."""

    def setUp(self):
        self.practice_a = Practice.objects.create(name="Practice A", subscription_tier="solo")
        self.practice_b = Practice.objects.create(name="Practice B", subscription_tier="group")

        self.doctor_a = User.objects.create_user(
            email="doc_a@test.com",
            password="DocAP@ss1!",
            role="doctor",
            first_name="Doc",
            last_name="A",
            practice=self.practice_a,
        )
        self.doctor_b = User.objects.create_user(
            email="doc_b@test.com",
            password="DocBP@ss1!",
            role="doctor",
            first_name="Doc",
            last_name="B",
            practice=self.practice_b,
        )

        self.patient_a = Patient.objects.create(
            practice=self.practice_a,
            first_name="Pat",
            last_name="A",
            date_of_birth=date(1990, 1, 1),
        )
        self.patient_b = Patient.objects.create(
            practice=self.practice_b,
            first_name="Pat",
            last_name="B",
            date_of_birth=date(1990, 1, 1),
        )

    def test_doctor_cannot_see_other_practice_patients(self):
        client = APIClient()
        client.force_authenticate(user=self.doctor_a)

        resp = client.get("/api/v1/patients/")
        self.assertEqual(resp.status_code, 200)
        patient_ids = [p["id"] for p in resp.data["results"]]
        self.assertIn(str(self.patient_a.id), patient_ids)
        self.assertNotIn(str(self.patient_b.id), patient_ids)

    def test_doctor_cannot_access_other_practice_patient(self):
        client = APIClient()
        client.force_authenticate(user=self.doctor_a)

        resp = client.get(f"/api/v1/patients/{self.patient_b.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_doctor_cannot_see_other_practice_encounters(self):
        enc_b = Encounter.objects.create(
            doctor=self.doctor_b,
            patient=self.patient_b,
            encounter_date=date.today(),
            input_method="paste",
        )

        client = APIClient()
        client.force_authenticate(user=self.doctor_a)

        resp = client.get(f"/api/v1/encounters/{enc_b.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_doctor_cannot_access_other_practice_note(self):
        enc_b = Encounter.objects.create(
            doctor=self.doctor_b,
            patient=self.patient_b,
            encounter_date=date.today(),
            input_method="paste",
            status="ready_for_review",
        )
        ClinicalNote.objects.create(
            encounter=enc_b,
            note_type="soap",
            subjective="S",
            objective="O",
            assessment="A",
            plan="P",
            ai_generated=True,
        )

        client = APIClient()
        client.force_authenticate(user=self.doctor_a)

        resp = client.get(f"/api/v1/encounters/{enc_b.id}/note/")
        self.assertEqual(resp.status_code, 404)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION="none",
)
class PracticeManagementPipelineTest(TestCase):
    """Test practice management flow: get practice, update, get stats."""

    def setUp(self):
        self.practice = Practice.objects.create(
            name="Management Clinic",
            subscription_tier="solo",
        )
        self.doctor = User.objects.create_user(
            email="mgmt_doc@test.com",
            password="MgmtP@ss1!",
            role="doctor",
            first_name="Mgmt",
            last_name="Doc",
            practice=self.practice,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.doctor)

    def test_practice_management_flow(self):
        # Get practice
        resp = self.api.get("/api/v1/practice/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name"], "Management Clinic")

        # Update practice
        resp = self.api.patch("/api/v1/practice/", {
            "name": "Updated Management Clinic",
            "address": "123 Main Street",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name"], "Updated Management Clinic")
        self.assertEqual(resp.data["address"], "123 Main Street")

        # Create some data for stats
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="Stats",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
        )
        Encounter.objects.create(
            doctor=self.doctor,
            patient=patient,
            encounter_date=date.today(),
            input_method="paste",
            status="uploading",
        )
        Encounter.objects.create(
            doctor=self.doctor,
            patient=patient,
            encounter_date=date.today(),
            input_method="paste",
            status="approved",
        )

        # Get stats
        resp = self.api.get("/api/v1/practice/stats/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total_patients"], 1)
        self.assertEqual(resp.data["total_encounters"], 2)
        self.assertIn("uploading", resp.data["encounters_by_status"])
        self.assertIn("approved", resp.data["encounters_by_status"])
        self.assertEqual(resp.data["encounters_by_status"]["uploading"], 1)
        self.assertEqual(resp.data["encounters_by_status"]["approved"], 1)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION="none",
)
class AuditTrailVerificationTest(TestCase):
    """Verify that audit logs are properly created for PHI access."""

    def setUp(self):
        self.practice = Practice.objects.create(
            name="Audit Clinic",
            subscription_tier="solo",
        )
        self.doctor = User.objects.create_user(
            email="audit_doc@test.com",
            password="AuditP@ss1!",
            role="doctor",
            first_name="Audit",
            last_name="Doc",
            practice=self.practice,
        )
        self.patient_record = Patient.objects.create(
            practice=self.practice,
            first_name="Audit",
            last_name="Patient",
            date_of_birth=date(1985, 8, 20),
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.doctor)

    def test_patient_list_creates_audit_entry(self):
        initial_count = AuditLog.objects.count()
        self.api.get("/api/v1/patients/")
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_patient_detail_creates_audit_with_resource_id(self):
        self.api.get(f"/api/v1/patients/{self.patient_record.id}/")
        log = AuditLog.objects.filter(
            resource_type="patient",
            action="view",
        ).latest("created_at")
        self.assertEqual(log.resource_id, self.patient_record.id)
        self.assertTrue(log.phi_accessed)

    def test_encounter_access_creates_audit_entry(self):
        enc = Encounter.objects.create(
            doctor=self.doctor,
            patient=self.patient_record,
            encounter_date=date.today(),
            input_method="paste",
        )
        self.api.get(f"/api/v1/encounters/{enc.id}/")
        log = AuditLog.objects.filter(
            resource_type="encounter",
            action="view",
        ).latest("created_at")
        self.assertEqual(log.resource_id, enc.id)

    def test_patient_create_creates_audit_entry(self):
        self.api.post("/api/v1/patients/", {
            "first_name": "New",
            "last_name": "AuditPat",
            "date_of_birth": "1995-01-01",
        }, format="json")
        log = AuditLog.objects.filter(
            resource_type="patient",
            action="create",
        ).latest("created_at")
        self.assertEqual(log.user, self.doctor)
        self.assertTrue(log.phi_accessed)

    def test_audit_logs_are_immutable(self):
        """Audit logs cannot be modified or deleted."""
        self.api.get("/api/v1/patients/")
        log = AuditLog.objects.latest("created_at")

        with self.assertRaises(Exception):
            log.action = "delete"
            log.save()

        with self.assertRaises(Exception):
            log.delete()
