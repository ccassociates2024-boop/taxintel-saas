# Phase 1 Productionisation Plan

**Project:** Indian AI-Powered Tax Intelligence Platform
**Target domain:** `app.associatepiyush.in` (frontend) + `api.associatepiyush.in` (backend)
**Scope:** Razorpay billing (GST-compliant), Digio e-sign, DigiLocker integration, WhatsApp Business API, custom-domain production deployment
**Author:** AI senior advisor draft for review
**Status:** DRAFT — awaiting sign-off before implementation

---

## 1. Codebase audit (what we are building on)

| Area | Present today | Path |
|---|---|---|
| Backend | FastAPI 0.115, SQLAlchemy 2, JWT (HS256), slowapi rate limiting | `backend/app/` |
| Frontend | Next.js 14.2, Tailwind, shadcn-style components | `frontend/app/`, `frontend/components/` |
| DB | Postgres 16, 8 tables, plain `CREATE TABLE` script | `database/schema.sql` |
| Microservices | `services/ais-parser`, `services/tax-recommendation-engine` | `services/` |
| Deployment | `docker-compose.yml` (local) + `railway.toml` + `frontend/vercel.json` | repo root |
| Migrations | `alembic` is in `requirements.txt` but **no `alembic/` directory exists yet** | — |
| Object storage | Local Docker volume `backend-uploads` — **will not survive Railway redeploys** | `docker-compose.yml` |
| Background jobs | None | — |
| Secrets | `JWT_SECRET=change-me-in-production` in env example | `backend/.env.example` |
| Multi-tenancy | Row-scoped by `owner_id` (one user = one tenant) — not true multi-user CA-firm model | `backend/app/db/models.py` |

These five gaps **must be closed before** any of the four integrations land, otherwise the integrations will compound the existing risk.

---

## 2. Phasing summary

| Phase | Workstream | Calendar effort (1 senior + 1 junior) | Blocking external dependency |
|---|---|---|---|
| 0 | Production foundation (Alembic, S3, Redis+worker, secrets, Sentry, idempotency, webhook helpers) | 1.5 weeks | — |
| 1A | Tenant model + JWT claims + plan-gating middleware | 1 week | — |
| 1B | Razorpay subscriptions + GST-compliant invoices | 2 weeks | Razorpay business KYC; CA firm GSTIN |
| 1C | Digio e-sign (engagement letters, consent, authorisation) | 1.5 weeks | Digio sandbox + prod onboarding (~5 working days) |
| 1D | DigiLocker citizen-consent ingestion (Form 16, PAN, Aadhaar) | 1.5 weeks | DigiLocker partner onboarding (NeGD; 3–6 weeks if not already approved) |
| 1E | WhatsApp Business API (Meta Cloud API direct) | 1.5 weeks | Meta WABA + display-name + template approval (1–2 weeks) |
| 1F | DNS, custom domains, cutover to `app.associatepiyush.in` | 0.5 week | DNS access + India-region Postgres (Railway / managed) |
| 1G | Hardening (PII encryption, audit log, observability, backups) | 1 week (concurrent) | — |

**Total elapsed:** ~9–10 weeks calendar, assuming partner onboarding starts day 1 of the project.

> Critical-path advice: kick off Razorpay KYC, Digio onboarding, DigiLocker partner application, and Meta WABA verification on **day 1** of Phase 0. None block Phase 0 code, but all block their respective phases later.

---

## 3. Phase 0 — Production foundation

Goal: get the existing app into a state where adding regulated integrations is safe.

### 3.1 Alembic migrations

- Add `backend/alembic/` (env.py, versions/, alembic.ini).
- Baseline revision = current `database/schema.sql`.
- Every subsequent schema change ships as a numbered revision; `database/schema.sql` becomes generated.
- Add `alembic upgrade head` to backend container start-up (or to a release job).

### 3.2 Redis + background worker

- Add `redis:7` to `docker-compose.yml` and as a Railway add-on.
- Adopt **ARQ** (lightweight, asyncio-native, good FastAPI fit) or **RQ** — recommend ARQ.
- Worker process under `backend/app/worker/` with queues: `default`, `billing`, `esign`, `digilocker`, `whatsapp`.
- Use cases queued here: webhook processing, polling Digio status, DigiLocker token refresh, WhatsApp send + status polling, PDF report generation.

### 3.3 Object storage (S3 / Cloudflare R2)

- Replace `UPLOAD_DIR` local-volume writes with `boto3` against S3-compatible bucket.
- Storage layout: `s3://<bucket>/tenants/{tenant_id}/clients/{client_id}/uploads/{uuid}/{filename}`.
- Pre-signed URLs for downloads, never serve through API.
- Region: **ap-south-1 (Mumbai)** for data-residency posture under DPDPA 2023 (cross-border transfer of PII is permitted only to notified countries; default to India).

### 3.4 Secrets & config

- Rotate `JWT_SECRET` to a 32-byte random per environment (use `python -c "import secrets;print(secrets.token_urlsafe(32))"`).
- Move all secrets to Railway environment variables; never commit `.env`.
- Add a new env var `PII_ENCRYPTION_KEY` (Fernet, 32 bytes URL-safe base64) for column-level PII encryption (PAN, Aadhaar, phone, email of clients).
- Document rotation runbook in `docs/SECRETS.md`.

### 3.5 Cross-cutting middleware

| Middleware | Location | Purpose |
|---|---|---|
| `RequestIdMiddleware` | `backend/app/core/middleware.py` | injects `X-Request-Id`, propagates to logs |
| `IdempotencyMiddleware` | same | `Idempotency-Key` header → stored in `idempotency_keys` table for 24h; replays exact response |
| `WebhookSignatureDep` | `backend/app/core/webhooks.py` | per-provider HMAC verification helpers (Razorpay, Digio, Meta) |
| Structured JSON logging | `backend/app/core/logging.py` | uses `structlog`; redacts PAN/Aadhaar in logs |
| Sentry | `backend/app/main.py` | `sentry_sdk.init(...)` with `before_send` PII scrubber |

### 3.6 PII encryption helper

- `backend/app/core/crypto.py` exposing `encrypt_pii(plaintext) -> str` and `decrypt_pii(ciphertext) -> str` (Fernet).
- SQLAlchemy `TypeDecorator` `EncryptedString` for transparent column encryption.
- Apply to: `clients.pan`, `clients.phone`, `clients.email` (forward-compatible; PII not currently encrypted at rest).
- Migration must re-encrypt existing rows in a single ALTER+UPDATE transaction.

### 3.7 New tables introduced in Phase 0

```sql
CREATE TABLE IF NOT EXISTS idempotency_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID,
    key VARCHAR(120) NOT NULL,
    request_hash CHAR(64) NOT NULL,
    response_status SMALLINT NOT NULL,
    response_body JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    expires_at TIMESTAMP NOT NULL,
    UNIQUE (tenant_id, key)
);
```

---

## 4. Phase 1A — Tenant model

Goal: convert single-user accounts into CA-firm tenants so subscriptions, invoices, and audit trails attach correctly.

### 4.1 Schema delta

```sql
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    legal_name VARCHAR(200) NOT NULL,
    trade_name VARCHAR(200),
    gstin VARCHAR(15),
    pan VARCHAR(10),
    place_of_supply_state_code VARCHAR(2) NOT NULL DEFAULT '07', -- Delhi default; CA-firm sets actual
    billing_email VARCHAR(255) NOT NULL,
    billing_address_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(24) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

ALTER TABLE users ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE clients ADD COLUMN tenant_id UUID REFERENCES tenants(id);
-- repeat for uploaded_files, ais_records, form26as_records, tax_computations,
-- recommendations, audit_logs; backfill from owner_id -> users.tenant_id.
```

### 4.2 JWT claims

- Add `tid` (tenant id), `tnm` (tenant trade_name), `rol` (role).
- `backend/app/api/deps.py` exposes `get_current_tenant()` dependency.
- All repository queries scoped by `tenant_id` (not `owner_id`) — find/replace + tests.

### 4.3 Plan-gating

- Reusable dependency `enforce_plan_limit("clients" | "documents_month")` raising HTTP 402 with upgrade URL when threshold hit.
- Limits read from `tenants.plan_id` → `plans.limits_json`.

---

## 5. Phase 1B — Razorpay billing (GST-compliant)

### 5.1 Schema

```sql
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(40) UNIQUE NOT NULL,            -- 'STARTER','PRO','FIRM'
    display_name VARCHAR(120) NOT NULL,
    monthly_inr NUMERIC(10,2) NOT NULL,
    annual_inr NUMERIC(10,2) NOT NULL,
    razorpay_plan_id_monthly VARCHAR(64),
    razorpay_plan_id_annual VARCHAR(64),
    limits_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    features_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    plan_id UUID NOT NULL REFERENCES plans(id),
    razorpay_subscription_id VARCHAR(64) UNIQUE,
    status VARCHAR(24) NOT NULL,                  -- created/authenticated/active/past_due/paused/cancelled
    billing_cycle VARCHAR(8) NOT NULL,            -- monthly/annual
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    subscription_id UUID REFERENCES subscriptions(id),
    invoice_number VARCHAR(32) UNIQUE NOT NULL,   -- e.g. APC/2026-27/00001 (per FY series)
    fy VARCHAR(7) NOT NULL,                       -- '2026-27'
    place_of_supply_state_code VARCHAR(2) NOT NULL,
    hsn_sac VARCHAR(8) NOT NULL DEFAULT '998314', -- IT services
    taxable_value NUMERIC(12,2) NOT NULL,
    cgst NUMERIC(12,2) NOT NULL DEFAULT 0,
    sgst NUMERIC(12,2) NOT NULL DEFAULT 0,
    igst NUMERIC(12,2) NOT NULL DEFAULT 0,
    cess NUMERIC(12,2) NOT NULL DEFAULT 0,
    total NUMERIC(12,2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    status VARCHAR(16) NOT NULL,                  -- issued/paid/refunded/cancelled
    razorpay_invoice_id VARCHAR(64),
    issued_at TIMESTAMP NOT NULL DEFAULT now(),
    paid_at TIMESTAMP,
    pdf_storage_path TEXT
);

CREATE TABLE billing_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(24) NOT NULL DEFAULT 'razorpay',
    provider_event_id VARCHAR(120) UNIQUE NOT NULL, -- idempotency
    event_type VARCHAR(64) NOT NULL,
    signature_verified BOOLEAN NOT NULL,
    payload_json JSONB NOT NULL,
    processed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
```

### 5.2 GST compliance notes (CGST Act, 2017)

- **Sec. 31 + Rule 46:** Tax invoice must carry invoice number (consecutive series ≤ 16 chars, unique per FY), date, supplier name + GSTIN + address, recipient name + GSTIN + address + state code, HSN/SAC, description, value, rate, amount of tax (CGST/SGST/IGST), place of supply, signature/DSC.
- **Intra-state (supplier state = POS):** charge CGST 9% + SGST 9%.
- **Inter-state:** charge IGST 18%.
- **SAC for SaaS/Information-technology services:** `998314`.
- **B2B above ₹5 cr aggregate turnover (FY 24-25):** e-invoicing via IRP + QR code mandatory. Plan now for IRP integration as a Phase 2 follow-up; current scope ships static PDF + QR placeholder.
- **TDS u/s 194J:** Some enterprise clients may withhold 10% TDS on professional services payments. Invoice template must include PAN of supplier and a TDS-applicability line.
- **Reverse charge:** mark "Whether tax is payable on reverse charge basis: No" for SaaS.
- **Cancellation/refund:** issue a credit note (CGST Sec. 34); link to original invoice.

### 5.3 Endpoints

```
GET    /api/v1/billing/plans                              public
POST   /api/v1/billing/subscriptions                      auth — body: {plan_code, billing_cycle}
GET    /api/v1/billing/subscription                       auth
POST   /api/v1/billing/subscriptions/cancel               auth
POST   /api/v1/billing/subscriptions/resume               auth
GET    /api/v1/billing/invoices                           auth
GET    /api/v1/billing/invoices/{id}.pdf                  auth — generated by reportlab
POST   /api/v1/billing/webhooks/razorpay                  public — HMAC-SHA256 verified
```

Razorpay webhook events handled (idempotent via `billing_events.provider_event_id`):
`subscription.activated`, `subscription.charged`, `subscription.completed`, `subscription.paused`, `subscription.cancelled`, `payment.failed`, `invoice.paid`, `refund.processed`.

### 5.4 Frontend pages

- `frontend/app/billing/page.tsx` — current plan, usage meters, next invoice date, manage button.
- `frontend/app/billing/plans/page.tsx` — plan picker; click → POST `/billing/subscriptions` → opens Razorpay checkout (`razorpay-checkout.js`).
- `frontend/app/billing/invoices/page.tsx` — list + download PDFs.
- `frontend/components/billing/PlanGate.tsx` — wraps any feature behind plan limit; renders upgrade modal on HTTP 402.

### 5.5 Env vars

```
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
BILLING_SUPPLIER_LEGAL_NAME=Associate Piyush & Co.
BILLING_SUPPLIER_TRADE_NAME=AssociatePiyush
BILLING_SUPPLIER_GSTIN=07XXXXXXXXXXXXX
BILLING_SUPPLIER_STATE_CODE=07
BILLING_SUPPLIER_ADDRESS_JSON='{"line1":"...","city":"...","state":"Delhi","pincode":"110001"}'
BILLING_INVOICE_PREFIX=APC
BILLING_HSN_SAC=998314
```

### 5.6 Risk & penalty register

| Risk | Penalty / consequence |
|---|---|
| Invoice without GSTIN or wrong POS | CGST Sec. 122 — ₹10,000 or amount of tax evaded, whichever higher |
| Non-issue of credit note for refund | Mismatch in GSTR-1 vs GSTR-3B; interest u/s 50 |
| Webhook replay → double subscription | Idempotency via `provider_event_id UNIQUE` |
| Razorpay key leak in client bundle | Use only `KEY_ID` on frontend; `KEY_SECRET` server-only |
| Failed renewal payment not surfaced | Email + WhatsApp + in-app banner on `subscription.charged` failure |

---

## 6. Phase 1C — Digio e-sign

Use case: CA firm sends engagement letter, ITR-filing consent, authority letter to client; client signs via Aadhaar OTP (electronic signature under IT Act 2000 Sec. 3A / Second Schedule); platform stores signed PDF + audit trail.

### 6.1 Schema

```sql
CREATE TABLE esign_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    code VARCHAR(48) NOT NULL,                -- 'engagement_letter','itr_consent','ais_authorisation'
    name VARCHAR(160) NOT NULL,
    body_md TEXT NOT NULL,                    -- mustache placeholders
    placeholders_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);

CREATE TABLE esign_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    template_id UUID REFERENCES esign_templates(id),
    document_type VARCHAR(48) NOT NULL,
    status VARCHAR(24) NOT NULL,              -- draft/sent/signed/declined/expired/cancelled
    digio_document_id VARCHAR(64) UNIQUE,
    unsigned_storage_path TEXT NOT NULL,
    signed_storage_path TEXT,
    signed_at TIMESTAMP,
    expires_at TIMESTAMP,
    audit_trail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE esign_signatories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES esign_documents(id) ON DELETE CASCADE,
    name VARCHAR(160) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(16) NOT NULL,
    role VARCHAR(48) NOT NULL,                -- 'CLIENT','CA','WITNESS'
    sign_method VARCHAR(24) NOT NULL,         -- 'aadhaar_otp','aadhaar_offline','electronic'
    sign_order SMALLINT NOT NULL DEFAULT 1,
    signed_at TIMESTAMP,
    ip VARCHAR(45),
    geo_json JSONB
);
```

### 6.2 Endpoints

```
POST /api/v1/esign/templates                    create/update template
GET  /api/v1/esign/templates
POST /api/v1/esign/documents                    create from template + send to Digio
GET  /api/v1/esign/documents
GET  /api/v1/esign/documents/{id}
POST /api/v1/esign/documents/{id}/remind
POST /api/v1/esign/documents/{id}/cancel
GET  /api/v1/esign/documents/{id}/signed.pdf
POST /api/v1/esign/webhooks/digio               HMAC-verified
```

### 6.3 Default templates shipped

1. `engagement_letter` — annual professional services engagement.
2. `itr_efiling_consent` — Sec. 139 e-filing authorisation.
3. `ais_authorisation` — client authorises CA firm to access AIS / 26AS / TIS on their behalf.
4. `digilocker_consent` — explicit consent under DPDPA 2023 for fetching documents from DigiLocker.

### 6.4 Env vars

```
DIGIO_CLIENT_ID=
DIGIO_CLIENT_SECRET=
DIGIO_BASE_URL=https://api.digio.in        # https://ext.digio.in for sandbox
DIGIO_WEBHOOK_SECRET=
DIGIO_DEFAULT_EXPIRY_DAYS=30
```

### 6.5 Risk register

| Risk | Mitigation |
|---|---|
| Tampered signed PDF | Digio returns hash; verify before storing; keep raw signed bytes in immutable S3 (versioning + object-lock if available) |
| Aadhaar number leakage | Never log raw Aadhaar; Digio masks; store only digio_document_id and audit trail |
| Repudiation of signature | Audit trail JSON includes Digio signer certificate fingerprint, IP, timestamp, geolocation; retain 8 years per ICAI doc-retention norms |

---

## 7. Phase 1D — DigiLocker integration

**Important legal reality check:** DigiLocker is a citizen-consent platform under NeGD / MeitY. A CA firm cannot directly fetch a client's documents; the **client** must authorise via DigiLocker OAuth in their own browser. After authorisation, a partner application can fetch the client's issued documents (Form 16, PAN, Aadhaar e-KYC, voter ID, driving licence, education certificates, vehicle RC).

> **AIS / 26AS / TIS are NOT presently exposed via DigiLocker.** The official channel remains the Income Tax e-filing portal, which only supports ITDREIN-based access for principal contacts. Plan calls this out so clients are not over-promised.

### 7.1 Schema

```sql
CREATE TABLE digilocker_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    digilocker_user_id VARCHAR(64),
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    consent_artifact_id VARCHAR(120),
    status VARCHAR(24) NOT NULL DEFAULT 'PENDING',  -- pending/linked/revoked/expired
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE digilocker_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    link_id UUID NOT NULL REFERENCES digilocker_links(id),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    doc_type VARCHAR(32) NOT NULL,                  -- 'PAN','AADHAAR','FORM16','DRIVING_LICENCE'
    digilocker_uri TEXT NOT NULL,
    file_hash CHAR(64),
    issued_by VARCHAR(160),
    issued_at DATE,
    uploaded_file_id UUID REFERENCES uploaded_files(id),
    fetched_at TIMESTAMP NOT NULL DEFAULT now()
);
```

### 7.2 OAuth flow

1. CA clicks **Invite client to DigiLocker** → backend creates a one-time signed magic link with `link_id`.
2. WhatsApp / email message delivered to client with the link (re-uses Phase 1E template `digilocker_invite_v1`).
3. Client opens link → backend redirects to DigiLocker authorise URL with PKCE.
4. DigiLocker → `GET /api/v1/digilocker/callback?code=...&state=link_id`.
5. Backend exchanges code → access + refresh token → encrypts with `PII_ENCRYPTION_KEY` → stores on `digilocker_links`.
6. Worker job `digilocker.sync(link_id)` pulls issued documents list.
7. For documents the CA configured to ingest, fetch and persist into `uploaded_files` (and trigger AIS parser if `FORM16`).

### 7.3 Endpoints

```
POST /api/v1/digilocker/links                      create + invite (CA)
GET  /api/v1/digilocker/links                      list links
GET  /api/v1/digilocker/links/{id}                 status
DELETE /api/v1/digilocker/links/{id}               revoke
GET  /api/v1/digilocker/oauth/{link_id}/start      client-facing
GET  /api/v1/digilocker/callback                   client-facing
POST /api/v1/digilocker/links/{id}/sync            trigger pull
POST /api/v1/digilocker/links/{id}/fetch           body: {uri}
```

### 7.4 Env vars

```
DIGILOCKER_CLIENT_ID=
DIGILOCKER_CLIENT_SECRET=
DIGILOCKER_REDIRECT_URI=https://api.associatepiyush.in/api/v1/digilocker/callback
DIGILOCKER_BASE_URL=https://api.digitallocker.gov.in
DIGILOCKER_AUTH_URL=https://api.digitallocker.gov.in/public/oauth2/1/authorize
DIGILOCKER_TOKEN_URL=https://api.digitallocker.gov.in/public/oauth2/1/token
```

### 7.5 Compliance & risk

- **DPDPA 2023 Sec. 6 (consent):** consent must be free, specific, informed, unconditional, unambiguous, with clear notice. The DigiLocker consent screen satisfies this; we additionally store the consent artifact ID and timestamp.
- **Right to erasure (DPDPA Sec. 12):** on client deletion, also revoke DigiLocker link and purge fetched docs.
- **Token at rest:** Fernet-encrypted using `PII_ENCRYPTION_KEY`; key never present in application logs.

---

## 8. Phase 1E — WhatsApp Business API (Meta Cloud API direct)

Why Meta Cloud API direct (no BSP): lowest cost, fastest iteration, native template management, suitable for India market.

### 8.1 Schema

```sql
CREATE TABLE whatsapp_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(80) NOT NULL,                 -- snake_case per Meta
    category VARCHAR(24) NOT NULL,             -- AUTHENTICATION / UTILITY / MARKETING
    language CHAR(5) NOT NULL DEFAULT 'en',
    body TEXT NOT NULL,
    header_type VARCHAR(16),                   -- TEXT/IMAGE/DOCUMENT/VIDEO/NONE
    footer TEXT,
    buttons_json JSONB,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING', -- PENDING/APPROVED/REJECTED/PAUSED
    meta_template_id VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name, language)
);

CREATE TABLE whatsapp_consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    phone VARCHAR(16) NOT NULL,
    opted_in_at TIMESTAMP NOT NULL DEFAULT now(),
    opted_in_source VARCHAR(48) NOT NULL,       -- 'onboarding','manual','digilocker_invite'
    opted_out_at TIMESTAMP,
    UNIQUE (tenant_id, phone)
);

CREATE TABLE whatsapp_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    client_id UUID REFERENCES clients(id),
    direction VARCHAR(8) NOT NULL,              -- 'out','in'
    template_id UUID REFERENCES whatsapp_templates(id),
    wa_message_id VARCHAR(80),                  -- Meta's wamid
    status VARCHAR(16),                         -- queued/sent/delivered/read/failed
    body_text TEXT,
    payload_json JSONB,
    error_json JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
```

### 8.2 Endpoints

```
POST /api/v1/whatsapp/templates                  submit to Meta for approval
GET  /api/v1/whatsapp/templates
POST /api/v1/whatsapp/messages                   send to client (consent + 24-hour window enforced)
GET  /api/v1/whatsapp/conversations/{client_id}
POST /api/v1/whatsapp/webhooks                   Meta verify-token GET + POST (HMAC SHA256 with app_secret)
POST /api/v1/whatsapp/consents/opt-in
POST /api/v1/whatsapp/consents/opt-out
```

### 8.3 Default templates to seed

| name | category | purpose |
|---|---|---|
| `tax_filing_reminder_v1` | UTILITY | Reminds client of impending due date with CA-firm CTA |
| `document_request_v1` | UTILITY | Requests a document upload, embeds magic link |
| `digilocker_invite_v1` | UTILITY | Sends DigiLocker authorisation link |
| `itr_acknowledgement_v1` | UTILITY | Shares ITR-V link after filing |
| `invoice_reminder_v1` | UTILITY | Razorpay invoice + pay link |
| `otp_login_v1` | AUTHENTICATION | OTP for client-portal login (when added) |

Meta template approval typically takes 1–24 hours per template. Submit during Phase 0.

### 8.4 Compliance

- **DPDPA 2023 + TRAI commercial-communications rules:** Maintain opt-in record; honour opt-out within 24 hours; never message non-consenting numbers.
- **24-hour customer-service window:** outside it, only `APPROVED` templates may be sent.
- **Marketing-template throttling:** Meta caps marketing template sends per number per day; UTILITY is unaffected.

### 8.5 Env vars

```
META_WABA_ID=
META_PHONE_NUMBER_ID=
META_ACCESS_TOKEN=                              # long-lived system-user token
META_APP_SECRET=                                # for webhook HMAC
META_WEBHOOK_VERIFY_TOKEN=
META_API_VERSION=v22.0
```

---

## 9. Phase 1F — Deployment to `app.associatepiyush.in`

### 9.1 Topology

```
Cloudflare DNS
├── associatepiyush.in          → Marketing site (out-of-scope; can be Webflow / Vercel project)
├── app.associatepiyush.in      → Vercel project "tax-intelligence-frontend"
└── api.associatepiyush.in      → Railway service "tax-intelligence-backend"
```

Both endpoints behind TLS 1.3 via provider-managed certificates.

### 9.2 DNS records (Cloudflare or registrar)

| Type | Name | Value | Proxy |
|---|---|---|---|
| CNAME | `app` | `cname.vercel-dns.com` | DNS-only |
| CNAME | `api` | `<railway-project>.up.railway.app` | DNS-only |
| TXT | `_vercel` | (Vercel-issued verification token) | — |
| TXT | (Railway custom-domain verification record) | — | — |

### 9.3 Backend changes for prod

- `CORS_ORIGINS=https://app.associatepiyush.in`
- `BASE_URL=https://api.associatepiyush.in`
- Trust proxy headers (`uvicorn --proxy-headers`)
- Cookie posture: continue Bearer-token only (no shared cookie domain) — simplest, safest.
- Health probe `/health` already exists; add `/ready` that checks DB + Redis.
- Postgres region: confirm Railway project is in **ap-south-1 (Mumbai)** or switch to a managed Postgres (Neon Mumbai / Supabase Mumbai / AWS RDS ap-south-1) for DPDPA posture.
- Daily `pg_dump` → S3 (ap-south-1) with 30-day retention.

### 9.4 Frontend changes for prod

- `NEXT_PUBLIC_API_URL=https://api.associatepiyush.in`
- Add `NEXT_PUBLIC_RAZORPAY_KEY_ID` (publishable) for checkout overlay.
- `frontend/vercel.json` — set `regions: ["bom1"]` for Mumbai edge.

### 9.5 Cutover checklist (T-0)

1. DB snapshot of current Railway DB.
2. Run Alembic to head.
3. Deploy backend with new env vars; verify `/health` and `/ready`.
4. Deploy frontend with new env vars.
5. Add Vercel + Railway custom domains; verify TLS issuance (~2 min).
6. Webhook-URL updates in Razorpay, Digio, Meta dashboards → new `api.associatepiyush.in/...` endpoints.
7. Smoke tests: register → login → create client → upload AIS → compute → recommend → subscribe → invoice → e-sign → DigiLocker invite → WhatsApp test.
8. Uptime monitor (Better Stack / UptimeRobot) pings `/health` every minute.
9. Sentry alert routes set.

### 9.6 Pre-go-live legal artifacts

- Privacy Policy hosted at `https://app.associatepiyush.in/privacy` — must disclose DPDPA basis, processor list (Razorpay, Digio, Meta, DigiLocker, OpenAI), retention, grievance officer.
- Terms of Service at `/terms` — limitation of liability, jurisdiction, governing law.
- Refund/Cancellation Policy at `/refunds` (Razorpay merchant requirement).
- Grievance Officer details (DPDPA Sec. 8(9)) and Data Principal complaint mechanism.

---

## 10. Phase 1G — Hardening (concurrent with all above)

| Item | Why |
|---|---|
| Replace local upload volume with S3 | Survive redeploys; pre-signed URLs |
| Fernet PII encryption on `clients.pan`, `clients.phone`, `clients.email` | DPDPA reasonable security safeguards |
| Webhook signature verification helper for Razorpay, Digio, Meta | Prevent spoofed events |
| Idempotency keys on all POSTs | Safe retries, especially for billing |
| ARQ background worker | Async webhooks, DigiLocker sync, WhatsApp delivery |
| `structlog` + Sentry + request IDs | Observability |
| pytest coverage ≥ 75% on billing, esign, digilocker, whatsapp | Regression safety |
| ruff + mypy + pre-commit | Code hygiene |
| Daily pg_dump → S3 (Mumbai), 30-day retention | Backups |
| ICAI 8-year retention runbook | Doc retention compliance |

---

## 11. New env-var summary (all phases)

```
# Phase 0
SENTRY_DSN=
REDIS_URL=
S3_ENDPOINT_URL=                          # blank for AWS, set for R2
S3_REGION=ap-south-1
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
PII_ENCRYPTION_KEY=                       # Fernet base64

# Phase 1B Razorpay
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
BILLING_SUPPLIER_LEGAL_NAME=
BILLING_SUPPLIER_TRADE_NAME=
BILLING_SUPPLIER_GSTIN=
BILLING_SUPPLIER_STATE_CODE=
BILLING_SUPPLIER_ADDRESS_JSON=
BILLING_INVOICE_PREFIX=APC
BILLING_HSN_SAC=998314

# Phase 1C Digio
DIGIO_CLIENT_ID=
DIGIO_CLIENT_SECRET=
DIGIO_BASE_URL=
DIGIO_WEBHOOK_SECRET=
DIGIO_DEFAULT_EXPIRY_DAYS=30

# Phase 1D DigiLocker
DIGILOCKER_CLIENT_ID=
DIGILOCKER_CLIENT_SECRET=
DIGILOCKER_REDIRECT_URI=
DIGILOCKER_BASE_URL=

# Phase 1E WhatsApp
META_WABA_ID=
META_PHONE_NUMBER_ID=
META_ACCESS_TOKEN=
META_APP_SECRET=
META_WEBHOOK_VERIFY_TOKEN=
META_API_VERSION=v22.0

# Phase 1F Prod
BASE_URL=https://api.associatepiyush.in
NEXT_PUBLIC_API_URL=https://api.associatepiyush.in
NEXT_PUBLIC_RAZORPAY_KEY_ID=
CORS_ORIGINS=https://app.associatepiyush.in
```

---

## 12. Open questions for the founder

1. **Billing entity & GSTIN** — what is the legal name, GSTIN, and registered address that should appear on every invoice? (Decides Phase 1B env defaults.)
2. **CA-firm GSTIN state code** — determines POS default and CGST/SGST vs IGST routing.
3. **Pricing plans** — final names and INR pricing (monthly + annual) for Starter / Pro / Firm; and feature/limits matrix.
4. **DigiLocker partner status** — already onboarded with NeGD, in application, or yet-to-apply? (Phase 1D blocker.)
5. **Digio account** — sandbox or production credentials available? Aadhaar OTP and Aadhaar offline both required?
6. **Meta WABA** — is the WhatsApp Business Account already verified with a display name? If not, kick off now (Phase 0 day 1).
7. **DNS provider** — Cloudflare or registrar's own DNS? Will affect Phase 1F record-setting playbook.
8. **Postgres region constraint** — willing to migrate to Mumbai-region managed Postgres, or stay on current Railway region?
9. **Object storage** — preference for AWS S3 (ap-south-1) vs Cloudflare R2 (lower egress, no native ap-south-1 region label)?
10. **Background-worker process budget** — Railway-hosted worker process (additional ~₹500/mo) acceptable, or accept synchronous webhook processing initially?

---

## 13. Recommended sequencing

1. **Week 0** — Founder answers Section 12; partner onboarding kick-off (Razorpay KYC, Digio, DigiLocker, Meta WABA).
2. **Weeks 1–2** — Phase 0 foundation (Alembic, Redis, S3, secrets, middleware, encryption helper).
3. **Week 3** — Phase 1A tenant model.
4. **Weeks 4–5** — Phase 1B Razorpay + GST invoicing.
5. **Weeks 5–6** — Phase 1C Digio e-sign (overlap with 1B late in week 5).
6. **Weeks 6–7** — Phase 1D DigiLocker (gated on partner approval).
7. **Weeks 7–8** — Phase 1E WhatsApp.
8. **Week 9** — Phase 1F cutover to `app.associatepiyush.in` + Phase 1G hardening sweep.

---

## 14. Definition of done for Phase 1

- A new CA firm can: register → subscribe to a plan → receive a GST-compliant invoice → onboard a client → send a DigiLocker authorisation request via WhatsApp → ingest Form 16 from DigiLocker → run tax computation → e-sign the engagement letter and ITR consent → file → share ITR-V via WhatsApp — entirely through `app.associatepiyush.in`, with all events audit-logged, all PII encrypted at rest, and all webhook events idempotent.
- Sentry + uptime monitor + daily backups live.
- Privacy Policy, Terms, Refunds, Grievance Officer all published.
