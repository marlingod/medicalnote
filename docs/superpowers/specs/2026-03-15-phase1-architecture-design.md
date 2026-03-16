# Phase 1 Architecture Design: Patient Post-Visit Summary Generator
**Date: March 15, 2026**

---

## Overview

Phase 1 of the MedicalNote platform — a **Patient Post-Visit Summary Generator** that also functions as an **AI clinical scribe**. Doctors record visits, paste notes, dictate, or scan handwritten notes. The system produces three outputs: a raw transcript, a structured SOAP note, and a patient-friendly summary delivered via mobile app or white-label clinic widget.

This is the "LAND" phase of a three-phase platform strategy:

```
Phase 1 (Months 1-6)     → Patient Post-Visit Summaries + AI Scribe  [LAND]
Phase 2 (Months 4-12)    → Specialty Smart Templates                  [EXPAND]
Phase 3 (Months 8-16)    → Clinical Note Quality Checker              [MONETIZE]
```

---

## Requirements Summary

| Dimension | Decision |
|-----------|----------|
| **Product** | Patient Post-Visit Summary Generator + Visit Recording/Transcription |
| **Backend** | Python (Django 5.x + DRF + django-allauth) |
| **Web Frontend** | TypeScript (Next.js) — Doctor Dashboard |
| **Mobile** | TypeScript (React Native) — Patient App |
| **Architecture** | Modular Monolith + Async Workers (Approach B) |
| **Target Market** | US first, global-ready architecture |
| **Users** | Doctor pays ($99-149/mo), patient receives summaries |
| **Input Methods** | Paste + Voice dictation + Photo/scan OCR + Visit recording |
| **Outputs** | Raw transcript + SOAP note + Patient summary |
| **Delivery** | Patient mobile app + White-label clinic widget |
| **Languages** | English + Spanish (i18n-ready for more) |
| **Cloud** | AWS (best healthcare-specific tooling: HealthScribe, Comprehend Medical, HealthLake) |
| **LLM** | Claude for Healthcare (HIPAA eligible, FHIR connectors) |
| **Compliance** | HIPAA from day 1, GDPR-ready architecture |

---

## Market Context (from Market Research Report)

### Why This Product

- **70% of patients** prefer AI-generated explanations over original clinical notes
- **OpenNotes mandate** (21st Century Cures Act) requires patient access to notes but average clinical notes are 13th grade reading level vs 7th-8th grade average US adult literacy
- **25M+ LEP individuals** in the US; ACA Section 1557 mandates language access
- **Competitors are weak**: Patiently AI (87.3% accuracy, standalone), Abridge (enterprise-only), EHR portals (share raw notes)
- **No competitor combines**: AI scribe + patient summary + multilingual + white-label

### Pricing Justification

AI scribes charge $99-299/mo (Freed $99, Abridge $250, DAX $600-800). This product offers scribe + patient summary — justifies **$99-149/provider/mo** positioning.

| Revenue Model | Price |
|---------------|-------|
| Solo provider (monthly) | $99/mo |
| Solo provider (annual) | $79/mo (billed annually) |
| Group practice (5+ providers) | $69/mo per provider |
| White-label (per clinic) | $299/mo + $2/summary |
| API access | $0.50-2.00/call |

### Regulatory Position

- **FDA**: Patient-facing summary generators are a gray area per Jan 2026 CDS guidance. Must include disclaimers ("informational purposes only, not medical advice"). Likely exempt if HCP reviews before delivery.
- **HIPAA**: BAA required with all cloud/AI vendors. AES-256 encryption at rest, TLS 1.3 in transit. Audit logging on all PHI access.
- **State consent laws**: Recording visits requires consent (two-party in some states). App must handle consent workflows.

---

## Architecture Decision: Modular Monolith + Async Workers (Approach B)

### Why This Approach

Three approaches were evaluated:

| Approach | MVP Time | Team Size | When It Fits |
|----------|----------|-----------|-------------|
| A: Monolith-First | 4-5 months | 1-2 devs | Ultra-simple product |
| **B: Modular Monolith + Workers** | **4-5 months** | **2-3 devs** | **Async-heavy processing (our case)** |
| C: Microservices | 8-10 months | 4-10+ devs | Proven product, large team |

**Approach B wins because:**
1. LLM calls, OCR, and speech-to-text are slow async operations (2-15 sec each) — workers prevent API blocking
2. Adding Phase 2/3 = adding new workers + routes, not a rewrite
3. 4-5 month MVP timeline aligns with market research target (4-8 months) — faster with Django batteries-included
4. AWS ECS Fargate + Celery fits this pattern perfectly
5. Every major AI scribe startup (Abridge, Freed, Nabla) started as monoliths

---

## Section 1: System Architecture Overview

```
+---------------------------------------------------------------------+
|                        CLIENT LAYER                                  |
|                                                                      |
|  +------------------+  +------------------+  +------------------+    |
|  |   Next.js Web    |  |  React Native    |  |  White-Label     |    |
|  |   (Doctor        |  |  (Patient App)   |  |  Widget SDK      |    |
|  |    Dashboard)    |  |                  |  |  (Embeddable)    |    |
|  |                  |  |  - View summary  |  |                  |    |
|  |  - Record visit  |  |  - Multi-lang    |  |  - iframe/JS     |    |
|  |  - Paste/dictate |  |  - Push notifs   |  |  - Clinic brand  |    |
|  |  - Upload photo  |  |  - History       |  |  - Custom domain |    |
|  |  - Review SOAP   |  |                  |  |                  |    |
|  |  - Edit & approve|  |                  |  |                  |    |
|  |  - Send summary  |  |                  |  |                  |    |
|  |  - Manage patients|  |                  |  |                  |    |
|  +--------+---------+  +--------+---------+  +--------+---------+    |
|           +----------------------+----------------------+            |
+----------------------------------+-----------------------------------+
                                   | HTTPS (TLS 1.3)
                                   v
+---------------------------------------------------------------------+
|                      API LAYER (Django + DRF)                              |
|                                                                      |
|  +----------+ +-----------+ +------------+ +--------------------+    |
|  | Auth &   | | Notes &   | | Recordings | | Patients &         |    |
|  | RBAC     | | Summaries | | API        | | Delivery API       |    |
|  |          | | API       | |            | |                    |    |
|  |- JWT     | |- CRUD     | |- Upload    | |- Patient registry  |    |
|  |- OAuth2  | |- Input    | |- Status    | |- Summary delivery  |    |
|  |- Roles   | |  methods  | |- Retrieve  | |- Push notifications|    |
|  |- API keys| |- Approve  | |  outputs   | |- White-label config|    |
|  +----------+ +-----------+ +------------+ +--------------------+    |
|                                                                      |
|  +------------------+  +----------------------------------------+    |
|  | Audit Logger     |  | HIPAA Middleware                       |    |
|  | (all PHI access) |  | (encryption, access control, logging) |    |
|  +------------------+  +----------------------------------------+    |
+------------------------------+---------------------------------------+
                                | publishes jobs
                                v
+---------------------------------------------------------------------+
|                     TASK QUEUE (Celery + Redis)                       |
+------------+--------------+--------------+--------------+------------+
             v              v              v              v
      +------------+ +------------+ +------------+ +------------+
      |Transcription| | SOAP Note | |  Summary   | |   OCR      |
      |  Worker    | |  Worker   | |  Worker    | |  Worker    |
      |            | |           | |            | |            |
      |- AWS       | |- Claude   | |- Claude    | |- AWS       |
      |  Health-   | |  API      | |  API       | |  Textract  |
      |  Scribe    | |           | |            | |            |
      |- Speaker   | |- SOAP     | |- Plain     | |- Document  |
      |  diarize   | |  structure| |  language   | |  AI        |
      |- Medical   | |- Medical  | |- Reading   | |- Handwrite |
      |  terms     | |  coding   | |  level adj | |  recog.    |
      |            | |           | |- EN/ES     | |            |
      +------------+ +------------+ +------------+ +------------+
                                |
                                v
+---------------------------------------------------------------------+
|                       DATA LAYER                                     |
|                                                                      |
|  +--------------+  +--------------+  +--------------------------+    |
|  | PostgreSQL   |  | S3|  | Redis                    |    |
|  | (encrypted)  |  | (HIPAA)      |  | (cache + queue)          |    |
|  |              |  |              |  |                          |    |
|  |- Users       |  |- Audio files |  |- Session cache           |    |
|  |- Notes       |  |- Scanned docs|  |- Job queue               |    |
|  |- Summaries   |  |- Transcripts |  |- Rate limiting           |    |
|  |- Patients    |  |              |  |                          |    |
|  |- Audit logs  |  |              |  |                          |    |
|  +--------------+  +--------------+  +--------------------------+    |
+---------------------------------------------------------------------+
```

### Key Design Decisions

- **4 async workers** handle all heavy processing — API stays fast (<200ms responses)
- **All PHI encrypted** at rest (AES-256) and in transit (TLS 1.3)
- **Audit logging** on every PHI access for HIPAA compliance

### Processing Pipelines

**Recording flow (full pipeline):**
```
Doctor records visit
    -> Audio uploaded to S3 (encrypted)
    -> Transcription Worker (medical ASR + speaker diarization)
    -> SOAP Note Worker (Claude API -> structured note)
    -> Summary Worker (Claude API -> patient-friendly, EN/ES)
    -> Doctor reviews/edits SOAP note
    -> Doctor approves -> Summary delivered to patient
```

**Paste/dictate flow (skip transcription):**
```
Doctor pastes/dictates clinical note
    -> SOAP Note Worker (if raw text, structure it)
    -> Summary Worker (generate patient summary)
    -> Doctor reviews/approves -> delivered
```

**Photo/scan flow (OCR first):**
```
Doctor photographs/uploads note
    -> OCR Worker (AWS Textract)
    -> SOAP Note Worker (structure extracted text)
    -> Summary Worker (generate patient summary)
    -> Doctor reviews/approves -> delivered
```

---

## Section 2: Data Model

### Core Entities

```
User (extends AbstractUser via accounts app)
├── id (UUID, PK)
├── email (EmailField, unique)              # allauth uses this as login
├── password (Django built-in)              # allauth handles hashing
├── role (CharField choices: doctor, admin, patient)
├── first_name (EncryptedCharField)         # django-encrypted-model-fields
├── last_name (EncryptedCharField)
├── phone (EncryptedCharField)
├── specialty (CharField, nullable)
├── license_number (CharField, nullable)
├── practice (ForeignKey -> Practice)
├── language_preference (CharField, default='en')
├── created_at (DateTimeField auto_now_add)
├── updated_at (DateTimeField auto_now)
├── is_active (BooleanField, Django built-in)  # soft delete via deactivation
│
├── [allauth provides]: email verification, MFA, social accounts
├── [Django provides]: groups, permissions, is_staff, last_login

practices
├── id (UUID, PK)
├── name
├── address (encrypted)
├── phone (encrypted)
├── subscription_tier (enum: solo, group, enterprise)
├── white_label_config (JSONB, nullable)
│   ├── logo_url
│   ├── brand_color
│   ├── custom_domain
│   └── widget_key
├── created_at
└── updated_at

patients
├── id (UUID, PK)
├── practice_id (FK -> practices)          # Patient belongs to practice, not a single doctor
├── first_name (EncryptedCharField)
├── last_name (EncryptedCharField)
├── name_search_hash (CharField, indexed)  # Blind index (HMAC-SHA256 of normalized name) for search
├── email (EncryptedCharField, nullable)
├── phone (EncryptedCharField, nullable)
├── date_of_birth (EncryptedDateField)
├── language_preference (CharField, default='en')
├── created_at
└── updated_at

Note: Any doctor within the same practice can create encounters with any patient.
The encounters table links specific doctors to specific patients per visit.

encounters
├── id (UUID, PK)
├── doctor_id (FK -> users)
├── patient_id (FK -> patients)
├── encounter_date
├── input_method (enum: recording, paste, dictation, scan)
├── status (enum: uploading, transcribing, generating_note, generating_summary,
│          ready_for_review, approved, delivered,
│          transcription_failed, note_generation_failed, summary_generation_failed)
├── consent_recording (boolean)
├── consent_timestamp
├── consent_method (enum: verbal, digital_checkbox, written)
├── consent_jurisdiction_state (CharField, 2-letter state code)
├── created_at
└── updated_at

recordings
├── id (UUID, PK)
├── encounter_id (FK -> encounters)
├── storage_url (S3 path, encrypted)
├── duration_seconds
├── file_size_bytes
├── format (enum: wav, mp3, webm)
├── transcription_status (enum: pending, processing, completed, failed)
├── created_at
└── deleted_at (auto-delete after retention period)

transcripts
├── id (UUID, PK)
├── encounter_id (FK -> encounters)
├── raw_text (encrypted)
├── speaker_segments (JSONB)
│   └── [{speaker: "doctor"|"patient", start: 0.0, end: 5.2, text: "..."}]
├── medical_terms_detected (JSONB)
├── confidence_score (float)
├── language_detected
├── created_at
└── updated_at

clinical_notes
├── id (UUID, PK)
├── encounter_id (FK -> encounters)
├── note_type (enum: soap, free_text, h_and_p)
├── subjective (encrypted)
├── objective (encrypted)
├── assessment (encrypted)
├── plan (encrypted)
├── raw_content (encrypted, for non-SOAP formats)
├── icd10_codes (JSONB)
├── cpt_codes (JSONB)
├── ai_generated (boolean)
├── doctor_edited (boolean)
├── approved_at (timestamp, nullable)
├── approved_by (FK -> users)
├── prompt_version_id (FK -> prompt_versions)
├── created_at
└── updated_at

patient_summaries
├── id (UUID, PK)
├── encounter_id (FK -> encounters)
├── clinical_note_id (FK -> clinical_notes)
├── summary_en (encrypted)
├── summary_es (encrypted, nullable)
├── reading_level (enum: grade_5, grade_8, grade_12)
├── medical_terms_explained (JSONB)
│   └── [{term: "hypertension", explanation: "high blood pressure"}]
├── disclaimer_text
├── delivery_status (enum: pending, sent, viewed, failed)
├── delivered_at (timestamp, nullable)
├── viewed_at (timestamp, nullable)
├── delivery_method (enum: app, widget, sms_link, email_link)
├── prompt_version_id (FK -> prompt_versions)
├── created_at
└── updated_at

audit_logs
├── id (UUID, PK)
├── user_id (FK -> users)
├── action (enum: view, create, update, delete, export, share)
├── resource_type (enum: patient, encounter, note, summary, recording)
├── resource_id (UUID)
├── ip_address
├── user_agent
├── phi_accessed (boolean)
├── details (JSONB)
├── created_at
└── (no update/delete — append-only)
```

### Relationships

```
Practice  1---* Users (doctors)
Practice  1---* Patients              # Patient belongs to practice, not single doctor
Doctor    1---* Encounters
Patient   1---* Encounters
Encounter 1---1 Recording (optional)
Encounter 1---1 Transcript (optional)
Encounter 1---1 Clinical Note
Encounter 1---1 Patient Summary
ClinicalNote    *---1 PromptVersion
PatientSummary  *---1 PromptVersion
User      1---* Audit Logs
```

---

## Section 3: Tech Stack

### Backend

| Component | Technology | Why |
|-----------|-----------|-----|
| **Framework** | Django 5.x + Django REST Framework | Batteries-included (admin, auth, ORM, migrations), mature ecosystem, CRUD-optimized |
| **ORM** | Django ORM (built-in) | Built-in migrations, model-first design, admin auto-generation |
| **Task Queue** | Celery + Redis + django-celery-beat | Deep Django integration, scheduled tasks, result backend |
| **Auth** | django-allauth + dj-rest-auth + simplejwt | Full auth system: registration, email verify, MFA (TOTP/WebAuthn), social login, JWT for API |
| **Serialization** | DRF Serializers | ModelSerializer for rapid CRUD, nested serialization, validation |
| **Field Encryption** | django-encrypted-model-fields | Drop-in PHI encryption for model fields |
| **Audit Logging** | django-auditlog | Automatic PHI access logging with zero custom code |
| **Filtering** | django-filter | Declarative queryset filtering for list endpoints |
| **WebSockets** | Django Channels + Redis | Real-time job status updates, processing progress |
| **Admin** | Django Admin (built-in) | Practice management, user admin, audit log viewer — free |
| **Testing** | pytest-django + factory-boy | Django-native test support, model factories |

### Frontend (Doctor Dashboard)

| Component | Technology | Why |
|-----------|-----------|-----|
| **Framework** | Next.js 15 (App Router) | SSR, API routes, file-based routing |
| **UI** | shadcn/ui + Tailwind CSS | Accessible components, rapid development |
| **State** | TanStack Query | Server state management, caching, optimistic updates |
| **Forms** | React Hook Form + Zod | Type-safe form validation |
| **Audio Recording** | MediaRecorder API + RecordRTC | Cross-browser audio capture |
| **Real-time** | WebSocket (via Django Channels) | Job status updates, processing progress |

### Mobile (Patient App)

| Component | Technology | Why |
|-----------|-----------|-----|
| **Framework** | React Native 0.76+ (New Architecture) | Cross-platform iOS/Android, shared TypeScript |
| **Navigation** | Expo Router | File-based routing, deep linking |
| **UI** | React Native Paper | Material Design 3, accessible |
| **Push Notifs** | Firebase Cloud Messaging (FCM) | Free, reliable, cross-platform |
| **Storage** | Expo SecureStore | Encrypted local storage for tokens |
| **i18n** | i18next + react-i18next | Industry standard, EN/ES support |

### Infrastructure (AWS)

**Why AWS over Google Cloud / Azure / Self-Hosted:**
- AWS HealthScribe is the **best medical speech-to-text** (31 specialties, speaker diarization, stateless) — this is the core feature
- **120+ HIPAA-eligible services** (largest catalog of any cloud provider)
- AWS Comprehend Medical unlocks Phase 2 (medical entity extraction for quality checker)
- AWS HealthLake unlocks Phase 3 (managed FHIR server for EHR integration)
- Largest Django deployment community and documentation
- ~$80/mo more than Google Cloud — worth it for the healthcare-specific tooling
- Self-hosted rejected: no DevOps team yet, HIPAA physical safeguards too burdensome for a startup

| Component | Technology | Why |
|-----------|-----------|-----|
| **Compute** | ECS Fargate | Auto-scaling, serverless containers, no server management, HIPAA eligible |
| **Database** | RDS (PostgreSQL 16) | Managed, HIPAA eligible, auto-backups, Multi-AZ failover |
| **Object Storage** | S3 (HIPAA bucket, SSE-KMS) | Audio files, scanned docs, encrypted at rest, lifecycle policies for auto-deletion |
| **Cache/Queue** | ElastiCache (Redis 7) | Managed Redis for Celery broker + session cache |
| **Speech-to-Text** | AWS HealthScribe | Purpose-built for clinical conversations, 31 specialties, speaker diarization, medical term extraction, stateless (no data stored), HIPAA eligible |
| **Medical NLP** | AWS Comprehend Medical | Medical entity extraction (medications, diagnoses, procedures) — used in Phase 2 quality checker |
| **OCR** | AWS Textract | Handwriting recognition, medical forms, table extraction |
| **LLM** | Claude for Healthcare (Anthropic API) | HIPAA eligible with BAA, best for medical text generation |
| **Push Notifications** | Amazon SNS + Firebase Cloud Messaging | SNS for SMS/email delivery, FCM for mobile push |
| **Monitoring** | CloudWatch + CloudTrail | HIPAA-compliant logging, audit trails, alerting |
| **Secrets** | AWS Secrets Manager | API keys, DB credentials, encryption keys, automatic rotation |
| **Key Management** | AWS KMS (FIPS 140-2 Level 3) | Envelope encryption for PHI fields, customer-managed keys |
| **CI/CD** | AWS CodePipeline + ECR | Container builds, automated deploys, approval gates |
| **CDN** | CloudFront | Static assets, widget SDK distribution, WAF integration |
| **Networking** | VPC + Private Subnets | Database and Redis in private subnets, no public internet access |
| **FHIR (Phase 3)** | AWS HealthLake | Managed FHIR R4 data store for EHR integration |

### Authentication Architecture (django-allauth + dj-rest-auth)

```
Auth Stack:
  django-allauth          → Registration, login, email verify, MFA (TOTP/WebAuthn), social login
  dj-rest-auth            → REST API endpoints for all of the above
  djangorestframework-simplejwt → JWT tokens for mobile app + widget API

Doctor Auth Flow (Web Dashboard):
  Email/password signup → email verification → login (session-based)
  Optional: Google social login (allauth provider)
  MFA: TOTP authenticator app (allauth built-in) — HIPAA compliance
  Session-based auth for web, JWT available for API calls

Patient Auth Flow (Mobile App):
  Phone + OTP (custom allauth adapter using Twilio)
  JWT token stored in Expo SecureStore
  Biometric login (device-level, app retrieves stored JWT)

Widget Auth:
  API key per practice (widget_key in Practice model)
  Time-limited signed summary tokens (24h expiry)
```

**Custom Patient OTP Adapter:**
```python
# apps/accounts/adapters.py
import hmac
from django.core.cache import cache

class PatientOTPAdapter(DefaultAccountAdapter):
    MAX_SEND_ATTEMPTS = 3       # Max OTP sends per phone per hour
    MAX_VERIFY_ATTEMPTS = 5     # Max verification attempts per OTP
    OTP_TIMEOUT = 300           # 5 minutes

    def send_otp(self, phone_number):
        # Rate limit: max 3 OTP sends per phone per hour
        send_key = f"otp_send_count:{phone_number}"
        send_count = cache.get(send_key, 0)
        if send_count >= self.MAX_SEND_ATTEMPTS:
            raise RateLimitExceeded("Too many OTP requests. Try again later.")

        code = generate_6_digit_otp()  # Must use secrets.SystemRandom (CSPRNG)
        phone_number = normalize_e164(phone_number)  # Normalize to E.164 before any cache key use
        cache.set(f"otp:{phone_number}", code, timeout=self.OTP_TIMEOUT)
        cache.set(f"otp_attempts:{phone_number}", 0, timeout=self.OTP_TIMEOUT)
        cache.set(send_key, send_count + 1, timeout=3600)  # 1 hour window

        try:
            twilio_client.messages.create(
                to=phone_number, body=f"Your MedicalNote code: {code}"
            )
        except TwilioRestException:
            # Fallback: could send via email if patient has one on file
            raise OTPDeliveryFailed("Could not send verification code.")

    def verify_otp(self, phone_number, code):
        # Rate limit: max 5 verification attempts per OTP
        attempts_key = f"otp_attempts:{phone_number}"
        attempts = cache.get(attempts_key, 0)
        if attempts >= self.MAX_VERIFY_ATTEMPTS:
            cache.delete(f"otp:{phone_number}")  # Invalidate OTP
            raise RateLimitExceeded("Too many attempts. Request a new code.")

        cache.set(attempts_key, attempts + 1, timeout=self.OTP_TIMEOUT)

        stored = cache.get(f"otp:{phone_number}")
        # Constant-time comparison to prevent timing attacks
        if stored and hmac.compare_digest(str(stored), str(code)):
            cache.delete(f"otp:{phone_number}")
            cache.delete(attempts_key)
            user, created = User.objects.get_or_create(
                phone=phone_number, defaults={"role": "patient"}
            )
            return user
        return None
```

### Field-Level Encryption

All PHI fields use **django-encrypted-model-fields** with AES-256-GCM envelope encryption:
- Data Encryption Key (DEK) per record, encrypted by a Key Encryption Key (KEK)
- KEK stored in AWS KMS (FIPS 140-2 Level 3)
- Enables key rotation without re-encrypting all data

---

## Section 4: API Design

### Authentication (via django-allauth + dj-rest-auth)

```
POST   /api/v1/auth/registration/           # Doctor registration (allauth)
POST   /api/v1/auth/login/                  # Login — returns JWT (simplejwt)
POST   /api/v1/auth/token/refresh/          # Refresh JWT token
POST   /api/v1/auth/password/reset/         # Password reset email (allauth)
POST   /api/v1/auth/password/reset/confirm/ # Confirm password reset
POST   /api/v1/auth/registration/verify-email/ # Email verification (allauth)
GET    /api/v1/auth/user/                   # Get current user profile
POST   /api/v1/auth/social/google/          # Google social login (allauth)
POST   /api/v1/auth/2fa/totp/              # Enable TOTP MFA (allauth)
POST   /api/v1/auth/patient/otp/send/       # Send OTP to patient phone (custom)
POST   /api/v1/auth/patient/otp/verify/     # Verify patient OTP (custom)
```

### Encounters

```
POST   /api/v1/encounters             # Create new encounter
GET    /api/v1/encounters             # List encounters (paginated)
GET    /api/v1/encounters/:id         # Get encounter with all outputs
PATCH  /api/v1/encounters/:id         # Update encounter status
DELETE /api/v1/encounters/:id         # Soft delete
```

### Input Methods

```
POST   /api/v1/encounters/:id/recording    # Upload audio recording
POST   /api/v1/encounters/:id/paste        # Paste clinical note text
POST   /api/v1/encounters/:id/dictation    # Submit dictated text
POST   /api/v1/encounters/:id/scan         # Upload photo/scanned doc
```

### Outputs

```
GET    /api/v1/encounters/:id/transcript    # Get raw transcript
GET    /api/v1/encounters/:id/note          # Get SOAP note
PATCH  /api/v1/encounters/:id/note          # Edit SOAP note
POST   /api/v1/encounters/:id/note/approve  # Approve SOAP note
GET    /api/v1/encounters/:id/summary       # Get patient summary
POST   /api/v1/encounters/:id/summary/send  # Deliver to patient
```

### Patients

```
POST   /api/v1/patients               # Register patient
GET    /api/v1/patients               # List patients (paginated)
GET    /api/v1/patients/:id           # Get patient details
PATCH  /api/v1/patients/:id           # Update patient
GET    /api/v1/patients/:id/summaries # Patient's summary history
```

### Patient-Facing (Authenticated via patient token)

```
GET    /api/v1/patient/summaries           # My summaries
GET    /api/v1/patient/summaries/:id       # View a summary
PATCH  /api/v1/patient/summaries/:id/read  # Mark as read
GET    /api/v1/patient/profile             # My profile
```

### White-Label Widget

```
GET    /api/v1/widget/config/:widget_key   # Get widget branding config
GET    /api/v1/widget/summary/:token       # Get summary by secure token
POST   /api/v1/widget/summary/:token/read  # Mark as viewed
```

### Admin / Practice Management

```
GET    /api/v1/practice                    # Practice details
PATCH  /api/v1/practice                    # Update practice
GET    /api/v1/practice/stats              # Dashboard analytics
GET    /api/v1/practice/audit-log          # Audit log (HIPAA)
POST   /api/v1/practice/white-label        # Configure white-label
```

### Job Status (WebSocket)

```
WS     /api/v1/ws/jobs/:encounter_id       # Real-time processing status
```

---

## Section 5: Processing Pipeline Detail

### Recording Pipeline (Full Flow)

```
Step 1: Audio Upload
  Client -> POST /encounters/:id/recording (multipart/form-data)
  API -> validates format (wav/mp3/webm, max 120 min)
  API -> sets encounter status -> "uploading"
  API -> uploads to S3 (encrypted bucket)
  API -> sets encounter status -> "transcribing"
  API -> publishes TRANSCRIPTION_JOB to Celery
  API -> returns 202 Accepted {job_id, status: "transcribing"}

Step 2: Transcription Worker
  Consumes TRANSCRIPTION_JOB
  Downloads audio from S3
  Calls AWS HealthScribe API:
    - 31 medical specialty models
    - Speaker diarization (doctor vs patient)
    - Medical term extraction + ontology mapping
    - Stateless processing (no audio stored by AWS)
  Saves transcript to DB (encrypted)
  Publishes SOAP_NOTE_JOB to Celery
  Updates encounter status -> "generating_note"
  Sends WebSocket update to client

Step 3: SOAP Note Worker
  Consumes SOAP_NOTE_JOB
  Loads transcript from DB
  Calls Claude for Healthcare API with prompt:
    System: "You are a medical documentation assistant..."
    Input: transcript with speaker labels
    Output: structured SOAP note (JSON)
      {
        subjective: "...",
        objective: "...",
        assessment: "...",
        plan: "...",
        icd10_codes: ["I10", "R60.0"],
        cpt_codes: ["99214"]
      }
  Validates LLM output against JSON schema (retry once if malformed)
  Saves clinical_note to DB (encrypted, with prompt_version reference)
  Publishes SUMMARY_JOB to Celery
  Updates encounter status -> "generating_summary"
  Sends WebSocket update to client

Step 4: Summary Worker
  Consumes SUMMARY_JOB
  Loads clinical_note from DB
  Calls Claude for Healthcare API with prompt:
    System: "Convert this clinical note to a patient-friendly summary..."
    Parameters:
      - reading_level: "grade_8"
      - language: "en" (and "es" if patient prefers Spanish)
      - include: medical term explanations
      - exclude: medical jargon without explanation
      - add: disclaimer text
  Validates output structure (retry once if malformed)
  Saves patient_summary to DB (encrypted, with prompt_version reference)
  Updates encounter status -> "ready_for_review" (only set AFTER both note + summary exist)
  Sends WebSocket update to client

Step 5: Doctor Review
  Doctor views transcript, SOAP note, and summary in dashboard
  Doctor edits SOAP note if needed (PATCH /note)
  If note edited -> re-triggers SUMMARY_JOB (regenerate summary)
  Doctor approves (POST /note/approve)
  Updates encounter status -> "approved"

Step 6: Delivery
  Doctor triggers delivery (POST /summary/send)
  System sends push notification to patient app
  (or generates secure link for widget delivery)
  Updates delivery_status -> "sent"
  When patient opens summary -> updates to "viewed"
```

### Processing Time Estimates

| Step | Duration | Service |
|------|----------|---------|
| Audio upload (30 min recording) | 5-15 sec | S3 |
| Transcription | 30-90 sec | AWS HealthScribe |
| SOAP note generation | 5-15 sec | Claude API |
| Summary generation (EN) | 3-8 sec | Claude API |
| Summary generation (ES) | 3-8 sec | Claude API |
| **Total (recording flow)** | **~1-3 min** | |
| **Total (paste flow)** | **~10-25 sec** | |

### Error Handling & Retry Strategy

Each worker follows a consistent error handling pattern:

| Worker | Retries | Backoff | Timeout | On Permanent Failure |
|--------|---------|---------|---------|---------------------|
| Transcription | 3 | Exponential (10s, 30s, 90s) | 5 min | Status -> `transcription_failed`, notify doctor |
| SOAP Note | 3 | Exponential (5s, 15s, 45s) | 2 min | Status -> `note_generation_failed`, notify doctor |
| Summary | 3 | Exponential (5s, 15s, 45s) | 2 min | Status -> `summary_generation_failed`, notify doctor |
| OCR | 3 | Exponential (5s, 15s, 45s) | 2 min | Status -> `transcription_failed`, notify doctor |

**Celery configuration:**
```python
# Retry policy applied to all workers
@app.task(bind=True, max_retries=3, default_retry_delay=10,
          retry_backoff=True, retry_backoff_max=90)
def transcription_task(self, encounter_id):
    try:
        # ... process
    except TransientError as exc:
        raise self.retry(exc=exc)
    except PermanentError:
        Encounter.objects.filter(id=encounter_id).update(
            status='transcription_failed'
        )
        notify_doctor_of_failure(encounter_id)
```

**Dead letter queue:** Failed jobs after max retries are routed to a `failed_jobs` Celery queue for manual inspection via Django Admin.

**Doctor notification on failure:** WebSocket push + in-app notification with "Retry" button. Doctor can manually retry from the encounter detail page, which re-enqueues the failed step.

**LLM output validation:** All Claude API responses are validated against a JSON schema before saving. If validation fails, the worker retries with a stricter prompt (adding explicit JSON formatting instructions). After 2 malformed responses, the job fails with `note_generation_failed`.

### Prompt Versioning

All LLM prompts are versioned and tracked:

```
prompt_versions
├── id (UUID, PK)
├── prompt_name (CharField: soap_note, patient_summary, medical_terms)
├── version (CharField: "1.0.0", "1.1.0")
├── template_text (TextField)
├── is_active (BooleanField)
├── created_at
└── updated_at
```

The `clinical_notes` and `patient_summaries` tables include a `prompt_version_id` FK, enabling full traceability of which prompt generated which output — critical for clinical validation and regulatory audits.

---

## Section 6: Security & HIPAA Compliance

### Encryption

| Layer | Method |
|-------|--------|
| Data in transit | TLS 1.3 (all connections) |
| Data at rest (DB) | AES-256-GCM field-level encryption for all PHI |
| Data at rest (files) | S3 SSE-KMS (customer-managed encryption keys) |
| Key management | AWS KMS (FIPS 140-2 Level 3) |
| Passwords | Argon2id (Django PASSWORD_HASHERS primary), bcrypt fallback |
| Patient summary links | Time-limited signed URLs (24h expiry) |

### Access Control

| Role | Permissions |
|------|------------|
| **Doctor** | CRUD own encounters, patients, notes. View own practice stats. |
| **Admin** | Doctor permissions + manage practice, users, white-label config, audit logs. |
| **Patient** | Read own summaries only. Mark as read. Update profile. |
| **API Key** (widget) | Read widget config. Read summaries by secure token. |

### HIPAA Technical Safeguards

| Requirement | Implementation |
|-------------|---------------|
| Access controls | Django permissions + groups (RBAC), DRF permission classes, row-level security |
| Audit controls | Append-only audit_logs table, all PHI access logged |
| Integrity controls | Database checksums, immutable audit trail |
| Transmission security | TLS 1.3, certificate pinning on mobile |
| Authentication | django-allauth (session + JWT via dj-rest-auth), MFA built-in (TOTP + WebAuthn) |
| Automatic logoff | 15-minute session timeout, configurable |
| Breach notification | Automated detection + alerting pipeline |
| BAAs | Required with: AWS, Anthropic (Claude), Twilio (SMS) |

### Data Retention

| Data Type | Retention | Reason |
|-----------|-----------|--------|
| Clinical notes | 7 years minimum | State medical record laws |
| Audio recordings | 90 days then auto-delete | Minimize PHI exposure |
| Transcripts | 7 years (linked to note) | Part of medical record |
| Patient summaries | 7 years | Part of medical record |
| Audit logs | 6 years | HIPAA requirement |
| Deleted accounts | 30-day soft delete, then purge non-required data | User right |

### Disaster Recovery (HIPAA 45 CFR 164.308(a)(7))

| Metric | Target |
|--------|--------|
| **RPO (Recovery Point Objective)** | < 1 hour |
| **RTO (Recovery Time Objective)** | < 4 hours |
| **Backup frequency** | RDS: continuous (point-in-time recovery, 35-day retention). S3: versioning enabled. |
| **Cross-region replication** | S3 audio files replicated to secondary region (us-west-2). RDS read replica in secondary region. |
| **Restore testing** | Monthly automated restore test to verify backup integrity |
| **Incident response** | Documented runbook in `docs/hipaa/incident-response.md` |

### Security Headers & CORS

| Header | Value |
|--------|-------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` (main app). Widget iframe uses CSP `frame-ancestors 'self' https://*.clinic-domain.com` instead (ALLOW-FROM is deprecated) |
| `Content-Security-Policy` | Strict CSP per app context |
| `X-XSS-Protection` | `0` (rely on CSP instead) |

**CORS policy:**
- Dashboard domain (`app.medicalnote.com`): full API access
- Widget origins (clinic custom domains): widget endpoints only
- Mobile app: all patient-facing endpoints via JWT

**API rate limiting:**
- Per-user: 100 req/min (authenticated)
- Per-API-key (widget): 60 req/min
- Per-IP (unauthenticated): 20 req/min
- Auth endpoints: 10 req/min per IP

---

## Section 7: White-Label Widget Architecture

### How It Works

Clinics embed a JavaScript snippet on their website/patient portal:

```html
<!-- MedicalNote Patient Summary Widget -->
<div id="medicalnote-widget"></div>
<script src="https://widget.medicalnote.app/v1/widget.js"
  data-widget-key="wk_abc123..."
  data-theme="light"
  data-lang="en">
</script>
```

### Widget Features

- Loads in an iframe (sandboxed, no access to host page)
- Styled with clinic's branding (logo, colors) from widget config
- Patient authenticates with a secure token (received via SMS/email)
- Displays summary with medical term tooltips
- Supports EN/ES toggle
- Responsive (works on desktop and mobile browsers)
- CSP headers prevent XSS

### Widget SDK Distribution

- Hosted on CloudFront CDN for global low-latency loading
- Versioned (v1, v2...) to prevent breaking changes
- < 50KB gzipped bundle size
- No external dependencies

---

## Section 8: Mobile App Architecture (Patient)

### Screens

```
Auth Flow:
  - Login (phone number + OTP)
  - Profile Setup (name, language preference)

Main Flow:
  - Summary List (all my visit summaries, sorted by date)
  - Summary Detail:
    - Visit date and doctor name
    - Patient-friendly summary text
    - Medical terms with tap-to-explain tooltips
    - Language toggle (EN/ES)
    - Disclaimer banner
    - "Contact my doctor" action
  - Profile/Settings:
    - Language preference
    - Notification preferences
    - Privacy controls
```

### Push Notification Flow

```
Doctor approves + sends summary
    -> Backend calls FCM API
    -> Patient receives push notification:
       "Dr. Smith shared your visit summary from March 15"
    -> Patient taps notification
    -> App opens Summary Detail screen
    -> Backend records "viewed" status
```

### Offline Support

- Summaries cached locally (encrypted with Expo SecureStore)
- Patient can read previously viewed summaries offline
- Sync when connection restored

---

## Section 9: Implementation Phases (Agent-Team Strategy)

Implementation will use **superpowers:dispatching-parallel-agents** and **superpowers:subagent-driven-development** skills to execute in parallel.

### Phase 1 Agent Team Structure

```
+------------------------------------------------------------------+
|  Lead Agent (Orchestrator)                                        |
|  - Manages dependencies between agents                           |
|  - Runs integration tests                                        |
|  - Handles cross-cutting concerns (shared types, configs)        |
+-------+------------+------------+------------+-------------------+
        |            |            |            |
        v            v            v            v
  +-----------+ +-----------+ +-----------+ +-----------+
  | Agent 1   | | Agent 2   | | Agent 3   | | Agent 4   |
  | Backend   | | Doctor    | | Patient   | | Widget    |
  | API +     | | Web App   | | Mobile    | | SDK       |
  | Workers   | | (Next.js) | | (React    | |           |
  | (Django)  | |           | |  Native)  | |           |
  +-----------+ +-----------+ +-----------+ +-----------+
  | - Models  | | - Auth UI | | - Auth    | | - JS SDK  |
  | - Auth    | | - Record  | | - Summary | | - iframe  |
  | - API     | |   visit   | |   list    | | - Theming |
  | - Celery  | | - Paste   | | - Summary | | - API     |
  |   workers | | - Review  | |   detail  | |   client  |
  | - Tests   | | - Approve | | - Push    | |           |
  |           | | - Send    | |   notifs  | |           |
  |           | | - Patient | | - i18n    | |           |
  |           | |   mgmt    | |           | |           |
  +-----------+ +-----------+ +-----------+ +-----------+
```

### Phase 2 Agent Team (Specialty Templates + Quality Checker)

```
  +-----------+ +-----------+ +-----------+
  | Agent 5   | | Agent 6   | | Agent 7   |
  | Template  | | Quality   | | Template  |
  | Engine    | | Checker   | | Market-   |
  | Backend   | | Worker    | | place UI  |
  +-----------+ +-----------+ +-----------+
  | - Template| | - Rules   | | - Browse  |
  |   CRUD    | |   engine  | | - Search  |
  | - AI auto | | - CMS     | | - Upload  |
  |   complete| |   rules   | | - Purchase|
  | - Specialty| | - Real-  | | - Ratings |
  |   configs | |   time    | |           |
  |           | |   scoring | |           |
  +-----------+ +-----------+ +-----------+
```

### Phase 3 Agent Team (Voice + Telehealth + EHR)

```
  +-----------+ +-----------+ +-----------+
  | Agent 8   | | Agent 9   | | Agent 10  |
  | Voice     | | Telehealth| | FHIR      |
  | Mobile    | | Doc       | | Integration|
  | Module    | | Module    | | Layer     |
  +-----------+ +-----------+ +-----------+
  | - On-     | | - Video   | | - FHIR R4 |
  |   device  | |   platform| |   client  |
  |   Whisper | |   APIs    | | - athena  |
  | - Offline | | - Consent | | - eClinical|
  |   mode    | |   engine  | | - Epic    |
  | - Voice   | | - POS/CPT | |   (SMART) |
  |   editing | |   auto    | | - Document|
  |           | | - Multi-  | |   push    |
  |           | |   state   | |           |
  +-----------+ +-----------+ +-----------+
```

---

## Section 10: Project Structure

```
medicalnote/
├── backend/
│   ├── manage.py                          # Django management entry
│   ├── config/                            # Django project config
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── base.py                    # Shared settings
│   │   │   ├── development.py             # Dev overrides
│   │   │   ├── production.py              # Prod overrides (HIPAA)
│   │   │   └── test.py                    # Test overrides
│   │   ├── urls.py                        # Root URL config
│   │   ├── wsgi.py                        # WSGI entry (ECS Fargate)
│   │   ├── asgi.py                        # ASGI entry (Channels/WebSocket)
│   │   └── celery.py                      # Celery app config
│   │
│   ├── apps/
│   │   ├── accounts/                      # User management (extends allauth)
│   │   │   ├── models.py                  # Custom User model, Practice
│   │   │   ├── admin.py                   # User/Practice admin
│   │   │   ├── serializers.py             # DRF serializers
│   │   │   ├── views.py                   # DRF viewsets
│   │   │   ├── urls.py
│   │   │   ├── adapters.py                # allauth adapters (patient OTP)
│   │   │   ├── permissions.py             # DRF permission classes
│   │   │   └── tests/
│   │   │
│   │   ├── patients/                      # Patient registry
│   │   │   ├── models.py                  # Patient model (encrypted fields)
│   │   │   ├── admin.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py                   # PatientViewSet
│   │   │   ├── urls.py
│   │   │   ├── filters.py                # django-filter filtersets
│   │   │   └── tests/
│   │   │
│   │   ├── encounters/                    # Core encounter management
│   │   │   ├── models.py                  # Encounter, Recording, Transcript
│   │   │   ├── admin.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py                   # EncounterViewSet + input endpoints
│   │   │   ├── urls.py
│   │   │   ├── filters.py
│   │   │   ├── signals.py                 # Post-save triggers for workers
│   │   │   └── tests/
│   │   │
│   │   ├── notes/                         # Clinical notes (SOAP)
│   │   │   ├── models.py                  # ClinicalNote (encrypted SOAP fields)
│   │   │   ├── admin.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py                   # Note review, edit, approve
│   │   │   ├── urls.py
│   │   │   └── tests/
│   │   │
│   │   ├── summaries/                     # Patient summaries + delivery
│   │   │   ├── models.py                  # PatientSummary (encrypted, i18n)
│   │   │   ├── admin.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py                   # Summary generation, delivery
│   │   │   ├── urls.py
│   │   │   ├── delivery.py                # Push notification + widget delivery
│   │   │   └── tests/
│   │   │
│   │   ├── widget/                        # White-label widget API
│   │   │   ├── models.py                  # WidgetConfig
│   │   │   ├── serializers.py
│   │   │   ├── views.py                   # Widget config + summary access
│   │   │   ├── urls.py
│   │   │   └── tests/
│   │   │
│   │   ├── audit/                         # HIPAA audit logging
│   │   │   ├── models.py                  # AuditLog (append-only)
│   │   │   ├── admin.py                   # Read-only audit log viewer
│   │   │   ├── middleware.py              # Auto-log PHI access
│   │   │   └── tests/
│   │   │
│   │   └── realtime/                      # WebSocket / Django Channels
│   │       ├── consumers.py               # Job status WebSocket consumer
│   │       ├── routing.py                 # Channel routing
│   │       └── tests/
│   │
│   ├── workers/                           # Celery workers (shared across apps)
│   │   ├── __init__.py
│   │   ├── transcription.py               # Audio -> transcript
│   │   ├── soap_note.py                   # Transcript -> SOAP note
│   │   ├── summary.py                     # Note -> patient summary
│   │   └── ocr.py                         # Image -> text
│   │
│   ├── services/                          # Shared service layer
│   │   ├── __init__.py
│   │   ├── llm_service.py                 # Claude API wrapper
│   │   ├── stt_service.py                 # AWS HealthScribe wrapper
│   │   ├── ocr_service.py                 # AWS Textract wrapper
│   │   ├── storage_service.py             # AWS S3 wrapper
│   │   └── notification_service.py        # FCM push notifications
│   │
│   ├── prompts/                           # LLM prompt templates
│   │   ├── soap_note.py
│   │   ├── patient_summary.py
│   │   └── medical_terms.py
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
│
├── web/                               # Doctor Dashboard (Next.js)
│   ├── src/
│   │   ├── app/                       # App Router pages
│   │   │   ├── (auth)/
│   │   │   │   ├── login/
│   │   │   │   └── register/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── encounters/
│   │   │   │   │   ├── new/           # New encounter (record/paste/scan)
│   │   │   │   │   ├── [id]/          # Review encounter outputs
│   │   │   │   │   └── page.tsx       # Encounter list
│   │   │   │   ├── patients/
│   │   │   │   └── settings/
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── audio-recorder.tsx
│   │   │   ├── note-editor.tsx        # SOAP note editor
│   │   │   ├── summary-preview.tsx
│   │   │   ├── scan-upload.tsx
│   │   │   └── processing-status.tsx  # WebSocket job status
│   │   ├── lib/
│   │   │   ├── api-client.ts          # Typed API client
│   │   │   └── websocket.ts
│   │   └── hooks/
│   ├── package.json
│   └── Dockerfile
│
├── mobile/                            # Patient App (React Native)
│   ├── app/                           # Expo Router
│   │   ├── (auth)/
│   │   │   └── login.tsx              # Phone + OTP
│   │   ├── (tabs)/
│   │   │   ├── summaries/
│   │   │   │   ├── index.tsx          # Summary list
│   │   │   │   └── [id].tsx           # Summary detail
│   │   │   └── profile.tsx
│   │   └── _layout.tsx
│   ├── components/
│   │   ├── summary-card.tsx
│   │   ├── medical-term-tooltip.tsx
│   │   └── language-toggle.tsx
│   ├── i18n/
│   │   ├── en.json
│   │   └── es.json
│   ├── package.json
│   └── app.json
│
├── widget/                            # White-Label Widget SDK
│   ├── src/
│   │   ├── index.ts                   # Widget entry point
│   │   ├── embed.ts                   # iframe creation + messaging
│   │   ├── theme.ts                   # Brand customization
│   │   └── api.ts                     # Widget API client
│   ├── dist/                          # Built widget.js
│   ├── package.json
│   └── rollup.config.js
│
├── infrastructure/                    # IaC
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── vpc.tf                         # VPC, subnets, security groups
│   │   ├── ecs.tf                         # ECS cluster, services, task defs
│   │   ├── rds.tf                         # PostgreSQL RDS instance
│   │   ├── s3.tf                          # HIPAA bucket + lifecycle policies
│   │   ├── elasticache.tf                 # Redis for Celery + cache
│   │   ├── kms.tf                         # CMK for PHI encryption
│   │   ├── alb.tf                         # Application Load Balancer
│   │   ├── cloudfront.tf                  # CDN for widget/static
│   │   └── variables.tf
│   └── docker-compose.yml             # Local development
│
├── docs/
│   ├── superpowers/
│   │   └── specs/
│   │       └── 2026-03-15-phase1-architecture-design.md (this file)
│   ├── api/                           # Generated API docs
│   └── hipaa/                         # HIPAA compliance docs
│
├── MARKET_RESEARCH_REPORT.md
├── TELEMEDICINE_DOCUMENTATION_INTEGRATION.md
└── README.md
```

---

## Section 11: Infrastructure & Deployment

### AWS Architecture

```
+------------------------------------------------------------------+
|  AWS Account (HIPAA-compliant, BAA signed)                        |
|                                                                    |
|  +-------------------+    +-------------------+                    |
|  | ECS Fargate       |    | ECS Fargate       |                    |
|  | (API Service)     |    | (Celery Workers)  |                    |
|  | - Django app      |    | - transcription   |                    |
|  | - Auto-scales     |    | - soap_note       |                    |
|  |   0-10 tasks      |    | - summary         |                    |
|  | - ALB in front    |    | - ocr             |                    |
|  +--------+----------+    +--------+----------+                    |
|           |                        |                               |
|  +--------v------------------------v----------+                    |
|  | VPC (private subnets)                      |                    |
|  |                                            |                    |
|  |  +----------------+  +----------------+    |                    |
|  |  | RDS            |  | ElastiCache    |    |                    |
|  |  | (PostgreSQL 16)|  | (Redis 7)      |    |                    |
|  |  | - Multi-AZ     |  | - Private IP   |    |                    |
|  |  | - Auto backup  |  | - Celery broker|    |                    |
|  |  | - Encrypted    |  | - Session cache|    |                    |
|  |  | - Private sub  |  |                |    |                    |
|  |  +----------------+  +----------------+    |                    |
|  +--------------------------------------------+                    |
|                                                                    |
|  +----------------+  +----------------+  +----------------+        |
|  | S3             |  | KMS            |  | Secrets Manager|        |
|  | (HIPAA bucket) |  | (FIPS 140-2    |  | (API keys,     |        |
|  | - Audio files  |  |  Level 3)      |  |  DB creds,     |        |
|  | - Scanned docs |  | - CMK for PHI  |  |  auto-rotate)  |        |
|  | - Lifecycle    |  |                |  |                |        |
|  |   policies     |  |                |  |                |        |
|  +----------------+  +----------------+  +----------------+        |
|                                                                    |
|  +----------------+  +----------------+  +----------------+        |
|  | CloudFront     |  | CodePipeline   |  | CloudWatch     |        |
|  | (widget SDK,   |  | + ECR          |  | + CloudTrail   |        |
|  |  static assets)|  | (CI/CD)        |  | (HIPAA logging)|        |
|  +----------------+  +----------------+  +----------------+        |
|                                                                    |
|  +----------------+  +----------------+                            |
|  | HealthScribe   |  | Comprehend     |                            |
|  | (medical STT,  |  | Medical        |                            |
|  |  31 specialties|  | (Phase 2: NLP) |                            |
|  |  stateless)    |  |                |                            |
|  +----------------+  +----------------+                            |
+------------------------------------------------------------------+
```

### Estimated Monthly Infrastructure Cost

| Service | Specs | Monthly Cost |
|---------|-------|-------------|
| ECS Fargate (API) | 2 vCPU, 4GB RAM, 2-5 tasks | $100-250 |
| ECS Fargate (Workers) | 4 vCPU, 8GB RAM, 1-3 tasks | $120-350 |
| RDS (PostgreSQL) | db.t3.medium, 100GB SSD, Multi-AZ | $170 |
| ElastiCache (Redis) | cache.t3.micro, 1 primary + 1 replica (Multi-AZ) | $90 |
| S3 | 100GB HIPAA bucket + lifecycle policies | $5 |
| KMS | 1 CMK, ~10K operations/mo | $5 |
| CloudFront | Widget SDK, static assets | $10 |
| ALB (Application Load Balancer) | 1 ALB | $25 |
| CloudWatch + CloudTrail | Logging + monitoring | $20 |
| CodePipeline + ECR | CI/CD + container registry | $10 |
| **Subtotal (infrastructure)** | | **$555-935/mo** |
| **External APIs** | | |
| Claude API (Anthropic) | ~5K encounters/mo | $200-500 |
| AWS HealthScribe | ~2.5K recordings/mo (avg 20min, $0.10/min) | $500-1,000 |
| AWS Textract | ~500 scans/mo | $25-50 |
| Twilio (SMS OTP) | ~2K messages/mo | $15 |
| FCM (push notifications) | Push notifications | $0 (free tier) |
| **Total estimated** | | **$1,295-2,500/mo** |

At $99/provider/mo, **breakeven at ~13-26 paying providers**.

**Note:** AWS HealthScribe is more expensive than Google Speech-to-Text ($0.10/min vs ~$0.04/min) but provides significantly better medical accuracy, speaker diarization, and medical term extraction — reducing downstream LLM costs and improving SOAP note quality.

---

## Success Criteria for Phase 1

| Metric | Target | How Measured |
|--------|--------|-------------|
| MVP launch | Within 4-5 months | Calendar milestone |
| Summary accuracy | >90% | Physician blind review of N=100 AI-generated summaries, scored on clinical accuracy (correct/incorrect/partially correct) |
| Time from recording to outputs | <3 minutes | Measured from `recording.created_at` to `encounter.status = ready_for_review`, tracked in CloudWatch |
| Time from paste to outputs | <30 seconds | Same approach, `encounter.created_at` to `ready_for_review` |
| Doctor approval rate (no edits) | >70% | `clinical_notes` where `doctor_edited = False AND approved_at IS NOT NULL` / total approved notes |
| Patient summary viewed rate | >60% | `patient_summaries` where `viewed_at IS NOT NULL` / total delivered summaries |
| First 50 paying providers | Within 3 months of launch | Stripe subscription count |
| System uptime | 99.5% | CloudWatch availability monitoring |
| HIPAA compliance audit | Pass before launch | Third-party HIPAA assessment or self-assessment checklist |
