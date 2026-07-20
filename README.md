# Lively Backend API

FastAPI backend for the Lively mobile app (MVP auth).

## Features (LA-2 / LA-31)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/signup` | Create parent account + send verification code |
| `POST` | `/api/v1/auth/login` | Authenticate and return JWT |
| `POST` | `/api/v1/auth/email/verify` | Verify email with code; returns JWT (no separate login needed) |
| `POST` | `/api/v1/auth/email/resend` | Resend verification code |
| `GET` | `/health` | Health check |

Social login (`/api/v1/auth/social`) is intentionally out of scope for this iteration.

## Stack

- FastAPI + Uvicorn
- **SQLAlchemy 2 ORM** (models, `Session`, relationships — no raw SQL in app code) + Alembic
- PostgreSQL (Neon)
- JWT (`python-jose`) + bcrypt password hashing

## Setup

### 1. Create virtual environment and install deps

```powershell
cd d:\Lively
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set:

- `DATABASE_URL` — Neon (or local) Postgres URL using `postgresql+psycopg2://...`
- `JWT_SECRET_KEY` — long random secret for production

### 3. Run migrations

```powershell
alembic upgrade head
```

### 4. Start the API

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Email verification (Brevo)

Verification codes are stored in Postgres and sent through **Brevo** transactional email.

Add these to `.env`:

```env
BREVO_API_KEY=xkeysib-...
BREVO_SENDER_EMAIL=noreply@yourdomain.com
BREVO_SENDER_NAME=Lively
```

Setup in Brevo:

1. Create an API key under **Settings → SMTP & API → API Keys**
2. Verify the sender email/domain under **Settings → Senders**

If `BREVO_API_KEY` / `BREVO_SENDER_EMAIL` are empty, the API still works in dev: the code is logged and can be returned in the JSON when `INCLUDE_VERIFICATION_CODE_IN_RESPONSE=true`.

Set `INCLUDE_VERIFICATION_CODE_IN_RESPONSE=false` once Brevo is live in production.
## Deploy to Render (dev / Singapore)

Prerequisites:
- GitHub repo with this code pushed to `main`
- Render workspace: **PEARL CRM**
- Region: **Singapore**
- Neon DB: **Lively Dev** (ap-southeast-2)

### Service settings

| Setting | Value |
|---------|-------|
| Name | `dev-lively-backend` |
| Runtime | Python 3.11 |
| Build | `pip install -r requirements.txt && alembic upgrade head` |
| Start | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |

`render.yaml` in the repo root defines this blueprint.

### Live dev URL

- **API:** https://dev-lively-backend.onrender.com
- **Health:** https://dev-lively-backend.onrender.com/health
- **Swagger:** https://dev-lively-backend.onrender.com/docs
- **Dashboard:** https://dashboard.render.com/web/srv-d9cubg1kh4rs73cccec0

**GitHub repo:** https://github.com/ayushrawat-psag/Lively (`development` branch)

### Required env vars (set in Render dashboard)

- `DATABASE_URL` — Neon Lively Dev connection string (`postgresql+psycopg2://...`)
- `JWT_SECRET_KEY`
- `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME`

## Tests

Install deps (includes pytest), then run:

```powershell
pip install -r requirements.txt
pytest
```

Coverage for the current MVP:

- Health check
- Signup / login / verify / resend (success + error cases)
- **Full E2E integration** (`test_integration_e2e.py`): DB persistence, Brevo email capture, JWT, contract shapes, Jira ACs
- Password hashing + JWT helpers
- Brevo email service (mocked HTTP)

Run only integration tests:

```powershell
pytest tests/test_integration_e2e.py -v
```

### Signup

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/signup `
  -H "Content-Type: application/json" `
  -d '{"name":"John Doe","email":"john@example.com","password":"Demo@123","guardian":true,"acceptedTerms":true}'
```

Expected: `201` with `emailVerificationRequired: true` and (in dev) `verificationCode`.

### Verify email

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/email/verify `
  -H "Content-Type: application/json" `
  -d '{"email":"john@example.com","code":"1234"}'
```

Expected: `200` with `token`, `user`, and `children` (empty array). The app can use this JWT immediately — no separate login needed after signup + verify.

### Resend verification

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/email/resend `
  -H "Content-Type: application/json" `
  -d '{"email":"john@example.com"}'
```

### Login (returning users)

Use login after the account is already verified (e.g. user closed the app post-verification, or a new device).

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"john@example.com","password":"Demo@123"}'
```

Expected: `200` with `token`, `user`, and `children` (empty array until child profiles exist).

### Login before verification

Returns `403` with `emailVerified: false`.

### Duplicate signup

If the email is **already verified**, signup returns `409` with `emailExists: true` — use login instead.

If the email exists but is **not yet verified** (e.g. user closed the app before entering the code), signup succeeds again: profile details are refreshed, a new verification code is sent, and the user can continue the verify flow.

## Project layout

```text
app/
  api/v1/endpoints/auth.py   # Auth routes
  core/config.py             # Settings from .env
  core/security.py           # Password + JWT helpers
  db/                        # Engine / session / Base
  models/                    # SQLAlchemy models
  repositories/              # DB access
  schemas/                   # Pydantic request/response contracts
  services/auth_service.py   # Auth business logic
  main.py                    # FastAPI app entry
alembic/versions/            # Migrations
```

## Notes on schema mapping

- API `name` is split into `users.first_name` / `users.last_name`
- API `guardian: true` maps to `user_type = Parent`
- `email_verified` and `accepted_terms` are stored on `users` for auth flows
- Primary keys are UUIDs per the MVP database schema
