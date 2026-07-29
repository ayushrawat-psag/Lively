# Lively Backend API

FastAPI backend for the Lively mobile app.

## Features

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/plans` | Monthly and yearly subscription plans |
| `POST` | `/api/v1/auth/signup` | Create parent account + send verification code |
| `POST` | `/api/v1/auth/login` | Parent login; returns JWT + children |
| `POST` | `/api/v1/auth/email/verify` | Verify email with OTP; returns JWT |
| `POST` | `/api/v1/auth/email/resend` | Resend verification code |
| `POST` | `/api/v1/auth/invite-code/regenerate` | Regenerate family invite code (Bearer JWT) |
| `POST` | `/api/v1/auth/child/verify-invite-code` | Validate invite code; list children for PIN login |
| `POST` | `/api/v1/auth/child/login` | Child PIN login; returns child JWT + `onBoarding` / `childAppTour` |
| `POST` | `/api/v1/children` | Create child profile (Bearer parent JWT) |
| `GET` | `/api/v1/children` | List children |
| `GET` | `/api/v1/children/{childId}` | Get child detail |
| `PATCH` | `/api/v1/children/{childId}` | Update child profile / PIN |
| `PATCH` | `/api/v1/children/{childId}/app-state` | Update `onBoarding` and/or `childAppTour` (parent or child JWT) |
| `DELETE` | `/api/v1/children/{childId}` | Soft-delete child |
| `GET` | `/api/v1/comic` | Fetch all island comics (optional `?islandId=` for one island; Bearer child JWT) |
| `POST` | `/api/v1/promo-code/validate` | Validate a promo / voucher code (Bearer JWT) |

Social login (`/api/v1/auth/social`) is intentionally out of scope for this iteration.

## Stack

- FastAPI + Uvicorn
- **SQLAlchemy 2 ORM** (models, `Session`, relationships — no raw SQL in app code) + Alembic
- PostgreSQL (Neon)
- JWT (`python-jose`) + bcrypt password hashing
- Campaign Monitor classic transactional email
- Docker / Coolify-ready (`Dockerfile` + `scripts/docker-entrypoint.sh`)

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

Edit `.env` and set at least:

- `DATABASE_URL` — Neon (or local) Postgres URL using `postgresql+psycopg2://...`
- `JWT_SECRET_KEY` — long random secret for production

Optional:

- `INVITE_CODE_FORMAT` — `alphanumeric` (default) or `numeric`
- `INVITE_CODE_LENGTH` — default `6`
- Campaign Monitor vars (see below)

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

Prefer `127.0.0.1` over `localhost` on Windows if IPv6 (`::1`) causes connection issues.

## Email verification (Campaign Monitor)

Verification codes are stored in Postgres and sent through **Campaign Monitor** classic transactional email (Jinja2 HTML/text templates under `app/email_templates/`).

Add these to `.env`:

```env
CAMPAIGN_MONITOR_API_KEY=...
CAMPAIGN_MONITOR_SENDER_EMAIL=support@areyoulively.com
CAMPAIGN_MONITOR_SENDER_NAME=Lively
CAMPAIGN_MONITOR_CLIENT_ID=
```

Setup in Campaign Monitor:

1. Create an API key under **Account Settings → API Keys**
2. Authenticate the sending domain (`areyoulively.com`) and enable custom authentication for transactional email
3. Set `CAMPAIGN_MONITOR_CLIENT_ID` if you use an account-level API key (not needed for client-specific keys)

Signup and resend **do not fail** when Campaign Monitor rejects or cannot deliver email — the account and verification code are still created. The response message indicates whether delivery succeeded. In development, use `verificationCode` from the JSON when `INCLUDE_VERIFICATION_CODE_IN_RESPONSE=true`.

If `CAMPAIGN_MONITOR_API_KEY` / `CAMPAIGN_MONITOR_SENDER_EMAIL` are empty, the API still works in dev: the code is logged and can be returned in the JSON when `INCLUDE_VERIFICATION_CODE_IN_RESPONSE=true`.

Set `INCLUDE_VERIFICATION_CODE_IN_RESPONSE=false` once email is live in production.

## Children & app state

Children are stored as `users` rows (`user_type = CHILD`, `is_child = true`) linked to a family.

On create:

- `onBoarding` defaults to `false`
- `childAppTour` defaults to `false`

Child PIN login (`POST /api/v1/auth/child/login`) returns these flags on the `child` object.

Update either or both flags:

```powershell
curl -X PATCH http://127.0.0.1:8000/api/v1/children/{childId}/app-state `
  -H "Authorization: Bearer <parent-or-child-token>" `
  -H "Content-Type: application/json" `
  -d '{"onBoarding":true,"childAppTour":true}'
```

- **Parent JWT** — may update any of their children
- **Child JWT** — may update only their own record
- At least one of `onBoarding` / `childAppTour` is required

## Deploy to Render (dev / Singapore)

Prerequisites:

- GitHub repo with this code pushed
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

**GitHub:** https://github.com/psag-sam/Lively-BackendServices (`development` branch)

### Required env vars (set in Render dashboard)

- `DATABASE_URL` — Neon Lively Dev connection string (`postgresql+psycopg2://...`)
- `JWT_SECRET_KEY`
- `CAMPAIGN_MONITOR_API_KEY`, `CAMPAIGN_MONITOR_SENDER_EMAIL`, `CAMPAIGN_MONITOR_SENDER_NAME`
- `CAMPAIGN_MONITOR_CLIENT_ID` (optional; required for account-level API keys)

### Docker / Coolify

```text
Dockerfile                    # python:3.11.6-slim
scripts/docker-entrypoint.sh  # alembic upgrade head, then uvicorn
```

Entrypoint runs migrations, then starts the API on `$PORT` (default `8000`).

## Tests

```powershell
pip install -r requirements.txt
pytest
```

Coverage includes:

- Health check
- Signup / login / verify / resend
- Plans + promo/voucher validation
- Children CRUD + app-state updates
- Child invite-code verify + PIN login
- Campaign Monitor email service (mocked HTTP)
- Full E2E integration (`test_integration_e2e.py`)

```powershell
pytest tests/test_integration_e2e.py tests/test_children.py tests/test_child_auth.py -q
```

## Quick API examples

### Signup

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/signup `
  -H "Content-Type: application/json" `
  -d '{"name":"John Doe","email":"john@example.com","password":"Demo@123","guardian":true,"acceptedTerms":true}'
```

Expected: `201` with `emailVerificationRequired: true` and (in dev) `verificationCode`.

### Plans

```powershell
curl -X GET http://127.0.0.1:8000/api/v1/plans
```

### Verify email

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/email/verify `
  -H "Content-Type: application/json" `
  -d '{"email":"john@example.com","code":"1234"}'
```

Expected: `200` with `token`, `user` (includes `inviteCode`), and `children`.

### Resend verification

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/email/resend `
  -H "Content-Type: application/json" `
  -d '{"email":"john@example.com"}'
```

### Login (returning users)

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"john@example.com","password":"Demo@123"}'
```

### Create child

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/children `
  -H "Authorization: Bearer <parent-token>" `
  -H "Content-Type: application/json" `
  -d '{"name":"Alex","dateOfBirth":"2015-06-20","gender":"boy","devices":["this_device"],"pin":"6756"}'
```

Expected: `201` with `onBoarding: false`, `childAppTour: false`, and echoed `pin`.

### Child login (invite → PIN)

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/child/verify-invite-code `
  -H "Content-Type: application/json" `
  -d '{"inviteCode":"ABC123"}'

curl -X POST http://127.0.0.1:8000/api/v1/auth/child/login `
  -H "Content-Type: application/json" `
  -d '{"childId":"<uuid>","pin":"6756"}'
```

### Auth edge cases

- Login before verification → `403` with `emailVerified: false`
- Duplicate signup when email is **already verified** → `409` with `emailExists: true`
- Duplicate signup when email exists but is **not verified** → succeeds again (profile refreshed, new code issued)

## Project layout

```text
app/
  api/v1/endpoints/
    auth.py           # Parent auth + child invite/PIN login
    children.py       # Children CRUD + app-state
    plans.py          # Subscription plans
    promo_codes.py    # Promo / voucher validation
  core/               # Settings, security, invite codes
  db/                 # Engine / session / Base
  email_templates/    # Verification HTML + text
  models/             # SQLAlchemy models (users, families, vouchers, …)
  repositories/       # DB access
  schemas/            # Pydantic request/response contracts
  services/           # Business logic
  main.py             # FastAPI app entry
alembic/versions/     # Migrations (through 012_add_child_app_tour)
scripts/
  docker-entrypoint.sh
  wipe_db.py
  generate_api_pdf.py
tests/
Dockerfile
render.yaml
```

## Notes on schema mapping

- API `name` is split into `users.first_name` / `users.last_name`
- API `guardian: true` maps to `user_type = PARENT`
- Children live on `users` (`user_type = CHILD`) with a `families` link
- Primary keys are UUIDs per the MVP database schema
- Promo codes map to the `vouchers` / `voucher_redemptions` tables

## App extensions beyond MVP PDF

The database follows the MVP PDF core schema, with a few app-specific extensions:

- `email_verification_codes` table for email OTP verification
- `users.email_verified` and `users.accepted_terms` for auth and legal state
- Child profile fields on `users`: `gender`, `devices`, `onboarding`, `child_app_tour`, `deleted_at`, `pin_hash`
- `PATCH /api/v1/children/{childId}/app-state` — update `onBoarding` and/or `childAppTour` (parent or child JWT)
- `voucher_redemptions` table for per-user voucher usage tracking
- `comic_pages` table for island comic page ordering and image URLs
- `islands.comic_number` stable zero-based public island id (Whirlpool is `0`)

Comic pages store only `image_url` references; binaries should remain in CRM-managed object storage/CDN.

`GET /api/v1/comic` returns every active island that has active comic pages in one response
so the mobile client can download once. Pass optional `?islandId=0` (the stable
`comic_number`) to return only that island.
