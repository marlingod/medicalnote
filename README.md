# MedicalNote

**AI-powered clinical documentation platform** that transforms doctor-patient encounters into structured medical notes and patient-friendly summaries.

Doctors record, paste, dictate, or scan clinical notes. The platform generates SOAP notes, patient summaries in plain language (English/Spanish), and quality scores against CMS compliance standards. Patients receive their summaries via a mobile app or an embeddable clinic widget.

---

## What It Does

```
Doctor records visit
    |
    v
Audio/Text/Photo input
    |
    v
AI Pipeline (AWS HealthScribe + Claude)
    |
    +---> Raw Transcript
    +---> Structured SOAP Note (doctor reviews/edits)
    +---> Patient-Friendly Summary (EN/ES)
    +---> Quality Score (CMS E/M compliance)
    |
    v
Doctor approves --> Patient receives summary via app/widget
```

### For Doctors
- **4 input methods**: Record visit audio, paste notes, voice dictation (Web Speech API), photo/scan (OCR)
- **AI-generated SOAP notes** from transcripts using Claude
- **Specialty templates** with AI auto-completion (Primary Care, Dermatology, Psychiatry)
- **Template marketplace** to browse, clone, rate, and share templates
- **Quality scoring** against CMS E/M documentation requirements (0-100 score with improvement suggestions)
- **Telehealth support** with auto-filled compliance fields (POS codes, CPT modifiers, state consent rules)
- **FHIR integration** to push approved notes to EHR systems (athenahealth, eClinicalWorks)

### For Patients
- **Plain-language summaries** at 8th-grade reading level
- **Medical term explanations** with tap-to-learn tooltips
- **Bilingual support** (English/Spanish toggle)
- **Push notifications** when a new summary is available
- **Offline access** to previously viewed summaries

### For Clinics
- **White-label widget** embeddable on any clinic website (5.7KB, zero dependencies)
- **Clinic branding** (logo, colors) applied automatically
- **Practice dashboard** with encounter stats and audit logs

---

## Architecture

```
                    +-----------------+     +------------------+
                    |  Next.js Web    |     |  React Native    |
                    |  (Doctor)       |     |  (Patient)       |
                    |  Port 9001      |     |  Port 9003       |
                    +--------+--------+     +--------+---------+
                             |                       |
                             v                       v
                    +-----------------------------------+      +--------------+
                    |        Django + DRF API            |      | Widget SDK   |
                    |        Port 9000                   |<---->| (Embeddable) |
                    |                                   |      | 5.7KB        |
                    |  12 Django Apps                    |      +--------------+
                    |  django-allauth + simplejwt        |
                    |  Django Channels (WebSocket)       |
                    +--------+---------+----------------+
                             |         |
                    +--------v--+  +---v-----------+
                    | PostgreSQL |  | Redis         |
                    | (encrypted)|  | (Celery + WS) |
                    +------------+  +---+-----------+
                                        |
                    +-------------------+-------------------+
                    |                   |                   |
              +-----v-----+    +-------v------+    +-------v------+
              |Transcription|   | SOAP Note    |   | Summary      |
              |Worker       |   | Worker       |   | Worker       |
              |HealthScribe |   | Claude API   |   | Claude API   |
              +-------------+   +--------------+   +--------------+
                    |
              +-----v-----+    +-------+------+
              | OCR Worker |   | Quality      |
              | Textract   |   | Checker      |
              +------------+   | CMS Rules    |
                               +--------------+
```

**Modular monolith** with async Celery workers. Heavy processing (transcription, LLM calls, OCR) runs in background workers so the API stays fast (<200ms). Workers chain automatically: Record -> Transcribe -> SOAP Note -> Summary -> Quality Score.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5.x, Django REST Framework, django-allauth, Celery, Django Channels |
| **Web Dashboard** | Next.js 15 (App Router), TypeScript, shadcn/ui, Tailwind CSS, TanStack Query |
| **Mobile App** | React Native (Expo), TypeScript, Expo Router, React Native Paper |
| **Widget SDK** | Vanilla TypeScript, Rollup, zero runtime dependencies |
| **Database** | PostgreSQL 16 (field-level PHI encryption) |
| **Cache/Queue** | Redis 7 (Celery broker + Django Channels + session cache) |
| **AI** | Claude API (SOAP notes, summaries, template auto-completion) |
| **Speech-to-Text** | AWS HealthScribe (31 medical specialties) |
| **OCR** | AWS Textract (handwriting recognition) |
| **Push Notifications** | Firebase Cloud Messaging |
| **Auth** | django-allauth (email/password + MFA + social login), phone OTP for patients |

---

## Project Structure

```
medicalnote/
├── backend/                          # Django API + Workers
│   ├── apps/
│   │   ├── accounts/                 # User, Practice, DeviceToken, auth
│   │   ├── patients/                 # Patient registry (encrypted PHI)
│   │   ├── encounters/               # Encounter pipeline (10 statuses)
│   │   ├── notes/                    # ClinicalNote, PromptVersion
│   │   ├── summaries/                # PatientSummary + delivery
│   │   ├── templates/                # Specialty templates + marketplace
│   │   ├── quality/                  # CMS E/M quality scoring
│   │   ├── telehealth/               # Multi-state compliance engine
│   │   ├── fhir/                     # FHIR R4 EHR integration
│   │   ├── widget/                   # White-label widget API
│   │   ├── audit/                    # HIPAA audit logging
│   │   └── realtime/                 # Django Channels WebSocket
│   ├── workers/                      # Celery tasks
│   │   ├── transcription.py          # Audio -> transcript (HealthScribe)
│   │   ├── soap_note.py              # Transcript -> SOAP note (Claude)
│   │   ├── summary.py                # Note -> patient summary (Claude)
│   │   ├── ocr.py                    # Image -> text (Textract)
│   │   └── quality_checker.py        # Note -> quality score (CMS rules)
│   ├── services/                     # External service wrappers
│   │   ├── llm_service.py            # Claude API
│   │   ├── stt_service.py            # AWS HealthScribe
│   │   ├── ocr_service.py            # AWS Textract
│   │   ├── storage_service.py        # AWS S3
│   │   ├── fhir_service.py           # FHIR R4 client
│   │   ├── notification_service.py   # Twilio SMS + Firebase FCM
│   │   ├── compliance_service.py     # Telehealth state compliance
│   │   ├── template_llm_service.py   # Template auto-completion
│   │   └── quality_rules_engine.py   # CMS scoring rules
│   └── prompts/                      # LLM prompt templates
│
├── web/                              # Doctor Dashboard (Next.js)
│   └── src/
│       ├── app/(auth)/               # Login, Register
│       ├── app/(dashboard)/          # Encounters, Templates, Patients, Settings
│       ├── components/               # UI components (shadcn/ui)
│       ├── hooks/                    # TanStack Query hooks
│       └── lib/                      # API client, auth context
│
├── mobile/                           # Patient App (React Native)
│   ├── app/(auth)/                   # Phone OTP login
│   ├── app/(tabs)/                   # Summaries, Profile
│   ├── components/                   # Summary card, tooltips, language toggle
│   └── services/                     # API client, offline cache, push notifications
│
├── widget/                           # Embeddable Widget SDK
│   ├── src/                          # TypeScript source
│   └── dist/widget.js                # Built bundle (5.7KB gzipped)
│
├── infrastructure/
│   └── docker-compose.yml            # Local dev (PostgreSQL + Redis + API + Celery)
│
└── docs/superpowers/
    ├── specs/                        # Architecture design spec
    └── plans/                        # Implementation plans (6 plans)
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16
- Redis 7

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create database
createdb medicalnote

# Set up environment
cp .env.example .env
# Edit .env with your API keys (ANTHROPIC_API_KEY, etc.)

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add the output to FIELD_ENCRYPTION_KEY in .env

# Run migrations
python manage.py migrate

# Seed specialty templates
python manage.py seed_templates

# Seed telehealth state rules (50 states + DC)
python manage.py seed_state_rules

# Create a doctor account
python manage.py createsuperuser

# Start API server
daphne -b 0.0.0.0 -p 9000 config.asgi:application

# In another terminal, start Celery worker
celery -A config worker -l info -Q default,transcription,soap_note,summary,ocr,quality --concurrency=2
```

### 2. Web Dashboard Setup

```bash
cd web

# Install dependencies
npm install

# Configure API URL
echo 'NEXT_PUBLIC_API_URL=http://localhost:9000/api/v1' > .env.local
echo 'NEXT_PUBLIC_WS_URL=ws://localhost:9000/api/v1/ws' >> .env.local

# Start dev server
npx next dev -p 9001
```

Open `http://localhost:9001` and log in.

### 3. Mobile App Setup

```bash
cd mobile

# Install dependencies
npm install

# Start Expo
npx expo start --port 9003
```

### 4. Widget SDK (Optional)

```bash
cd widget

# Install and build
npm install
npm run build

# Serve locally
npx serve dist -l 9002
```

### Using Docker Compose (Alternative)

```bash
cd infrastructure
docker-compose up -d
```

This starts PostgreSQL, Redis, Django API, and Celery worker.

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/registration/` | Doctor registration |
| POST | `/api/v1/auth/login/` | Login (returns JWT) |
| POST | `/api/v1/auth/token/refresh/` | Refresh JWT |
| POST | `/api/v1/auth/patient/otp/send/` | Send OTP to patient phone |
| POST | `/api/v1/auth/patient/otp/verify/` | Verify patient OTP |

### Encounters
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/encounters/` | Create encounter |
| POST | `/api/v1/encounters/:id/paste/` | Submit pasted text |
| POST | `/api/v1/encounters/:id/recording/` | Upload audio recording |
| POST | `/api/v1/encounters/:id/dictation/` | Submit dictated text |
| POST | `/api/v1/encounters/:id/scan/` | Upload photo/scan |
| GET | `/api/v1/encounters/:id/transcript/` | Get transcript |
| GET | `/api/v1/encounters/:id/note/` | Get SOAP note |
| POST | `/api/v1/encounters/:id/note/approve/` | Approve note |
| GET | `/api/v1/encounters/:id/summary/` | Get patient summary |
| POST | `/api/v1/encounters/:id/summary/send/` | Deliver to patient |

### Templates
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/templates/` | List/search templates |
| POST | `/api/v1/templates/:id/clone/` | Clone template |
| POST | `/api/v1/templates/:id/rate/` | Rate template (1-5) |
| POST | `/api/v1/templates/:id/auto-complete/` | AI auto-complete section |
| GET | `/api/v1/templates/specialties/` | List specialties |

### Quality & Telehealth
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/encounters/:id/quality/` | Get quality score |
| POST | `/api/v1/encounters/:id/telehealth/` | Add telehealth metadata |
| POST | `/api/v1/encounters/:id/fhir/push/` | Push note to EHR |

### Widget
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/widget/config/:key/` | Get clinic branding |
| GET | `/api/v1/widget/summary/:token/` | Get summary by secure token |

---

## HIPAA Compliance

- **Encryption at rest**: AES-256 field-level encryption for all PHI (names, phone, DOB, clinical notes)
- **Encryption in transit**: TLS 1.3 on all connections
- **Audit logging**: Append-only audit trail on every PHI access
- **Access control**: Role-based (doctor, admin, patient) with practice-level isolation
- **Authentication**: Argon2id password hashing, MFA support (TOTP + WebAuthn)
- **Data retention**: 7-year clinical records, 90-day audio auto-delete, 6-year audit logs
- **Session timeout**: 15-minute configurable auto-logoff

---

## Testing

```bash
# Backend unit tests
cd backend && python -m pytest apps/ workers/ services/ -v

# Backend integration/E2E tests
cd backend && python -m pytest tests/ -v

# Web dashboard tests
cd web && npx vitest run

# Mobile app tests
cd mobile && npx jest

# Widget SDK tests
cd widget && npx vitest run
```

**Test coverage**: ~565 tests across all components.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DJANGO_SECRET_KEY` | Yes | Django secret key |
| `FIELD_ENCRYPTION_KEY` | Yes | Fernet key for PHI encryption |
| `DB_NAME` | Yes | PostgreSQL database name |
| `DB_USER` | Yes | PostgreSQL user |
| `DB_PASSWORD` | Yes | PostgreSQL password |
| `ANTHROPIC_API_KEY` | Yes | Claude API key for AI features |
| `AWS_REGION` | For STT/OCR | AWS region for HealthScribe/Textract |
| `AWS_S3_BUCKET` | For storage | S3 bucket for audio/scans |
| `TWILIO_ACCOUNT_SID` | For SMS | Twilio account for patient OTP |
| `TWILIO_AUTH_TOKEN` | For SMS | Twilio auth token |
| `FIREBASE_CREDENTIALS_JSON` | For push | Firebase Admin SDK credentials |

See `backend/.env.example` for the full list.

---

## Roadmap

- [x] **Phase 1**: Patient Post-Visit Summary Generator + AI Scribe
- [x] **Phase 2**: Specialty Smart Templates + Template Marketplace + Quality Checker
- [x] **Phase 3**: Telehealth Documentation + FHIR EHR Integration
- [ ] **Phase 4**: Enterprise features (multi-provider practices, SSO, advanced analytics)
- [ ] **Phase 5**: International expansion (GDPR compliance, additional languages)

---

## License

Proprietary. All rights reserved.

---

## Market Context

- Clinical documentation software market: **$0.98B** (2024) growing to **$3.28B** by 2033
- Physicians spend **49% of their workday** on EHR/documentation vs 33% on patient care
- **70% of patients** prefer AI-generated explanations over raw clinical notes
- No existing product combines: AI scribe + patient summary + multilingual + quality scoring + telehealth compliance + white-label widget

See `MARKET_RESEARCH_REPORT.md` for the full analysis.
