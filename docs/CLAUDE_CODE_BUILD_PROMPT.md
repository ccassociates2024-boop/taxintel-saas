# Claude Code build prompt — Phase 1 productionisation

Copy everything between the two `---PROMPT START---` / `---PROMPT END---` markers into Claude Code (run it from inside the repo root, i.e. `C:\Users\Piyush\OneDrive\Desktop\office work\LECTURE TIME\Codex\2026-05-08\act-as-a-senior-fintech-saas`).

If any default below is wrong (GSTIN, plan pricing, etc.), search-and-replace **before** pasting. The prompt assumes the defaults are correct.

---PROMPT START---

You are a senior full-stack engineer working on an Indian fintech SaaS. The repo is already on disk at the current working directory. Read `README.md`, `docs/API.md`, `docs/DEPLOYMENT.md`, `database/schema.sql`, `docker-compose.yml`, `backend/app/main.py`, `backend/app/db/models.py`, `backend/app/core/config.py`, `backend/requirements.txt`, and `frontend/package.json` before writing a single line of code. Then read `docs/PHASE_1_PRODUCTIONISATION_PLAN.md` for the full design context — that document is your design spec and you must implement it faithfully.

## Mission

Productionise the platform for live use under the domain `app.associatepiyush.in`. Add: (1) Razorpay subscriptions with GST-compliant invoicing, (2) Digio e-sign, (3) DigiLocker citizen-consent ingestion, (4) WhatsApp Business API via Meta Cloud API, (5) custom-domain deployment to Railway + Vercel, plus a production-grade foundation that all four integrations need.

## Non-negotiable engineering standards

1. **Alembic for every schema change.** Initialise `backend/alembic/` if it does not exist, baseline against the current `database/schema.sql`, and ship one numbered revision per logical change. Never edit `database/schema.sql` by hand again — regenerate it from `alembic upgrade head` into a fresh DB and `pg_dump --schema-only` as a final step per phase.
2. **Tests for every new module.** `pytest` with `pytest-asyncio` and `httpx.AsyncClient` for FastAPI; coverage target ≥ 75% on every new module. Each provider integration (Razorpay, Digio, DigiLocker, Meta) gets a `tests/unit/` (using mocks of the HTTP client) and a `tests/integration/` (skipped unless sandbox env vars are present).
3. **Idempotency on every external webhook.** Use the `billing_events`-style pattern (provider_event_id UNIQUE). No webhook handler is allowed to run business logic unless `signature_verified=true`.
4. **PII encryption at rest** for `clients.pan`, `clients.phone`, `clients.email`, `digilocker_links.access_token`, `digilocker_links.refresh_token` via a `Fernet`-backed `EncryptedString` SQLAlchemy `TypeDecorator` in `backend/app/core/crypto.py`. Encryption key = env `PII_ENCRYPTION_KEY`.
5. **No secrets in code or git.** Update `backend/.env.example` and `frontend/.env.example` with every new variable; never commit real values.
6. **Structured JSON logging** via `structlog`; redact PAN, Aadhaar, access tokens, OTPs. Add Sentry SDK init in `backend/app/main.py` gated on `SENTRY_DSN`.
7. **Background worker.** Add `redis:7` to `docker-compose.yml`, adopt **ARQ** (asyncio-native), worker lives at `backend/app/worker/` and is started by a separate container `worker` in compose. Queues: `default`, `billing`, `esign`, `digilocker`, `whatsapp`.
8. **Object storage abstraction.** New module `backend/app/core/storage.py` with `put_bytes()`, `get_signed_url()`, `delete()`. Backed by `boto3` against S3 (works with AWS S3 ap-south-1 and Cloudflare R2). Local dev uses MinIO (add to docker-compose). All upload code paths route through this module — no more local-disk writes.
9. **DPDPA-aware retention.** Default ICAI retention 8 years; expose a `retention_policy` constant; honour soft-delete with `deleted_at` on client-data tables that store PII. Hard-delete only via worker job after retention window.
10. **Frontend follows the existing shadcn-style pattern** in `frontend/components/ui/`. New pages live under `frontend/app/`. State via React Server Components where possible; client components only where needed.

## Phasing — implement strictly in this order

After each phase: commit with a conventional-commits message, run the full test suite, regenerate `database/schema.sql` from Alembic, and pause for me to review.

### Phase 0 — foundation

- `backend/alembic/` with baseline `0001_baseline.py` matching today's schema.
- `redis:7` service in `docker-compose.yml`; `REDIS_URL` env var.
- `worker` service in `docker-compose.yml` running `arq backend.app.worker.WorkerSettings`.
- `minio:latest` service in `docker-compose.yml`; `S3_*` env vars wired.
- `backend/app/core/storage.py` (S3 abstraction) + replace all local-disk upload writes in `backend/app/api/uploads.py` and `backend/app/services/parsers.py`.
- `backend/app/core/crypto.py` (Fernet PII helper + `EncryptedString` TypeDecorator).
- `backend/app/core/middleware.py` (RequestId, Idempotency) + `idempotency_keys` table.
- `backend/app/core/webhooks.py` (HMAC verification helpers: `verify_razorpay()`, `verify_digio()`, `verify_meta()`).
- `backend/app/core/logging.py` (structlog config + PII redactor).
- Sentry init in `backend/app/main.py` gated on `SENTRY_DSN`.
- Generate a new `JWT_SECRET` default in `.env.example` using `python -c "import secrets;print(secrets.token_urlsafe(32))"` (commit the generated value as the example only).
- `pytest` + `pytest-asyncio` + `pytest-cov` + `httpx` + `freezegun` in `requirements-dev.txt`.
- `ruff` + `mypy` + `pre-commit` configured.
- **Definition of done:** `docker-compose up` brings up postgres + redis + minio + backend + worker + frontend; `pytest` green; `alembic upgrade head` is the only DDL path.

### Phase 1A — tenant model

- Alembic revision `0002_tenants.py`:
  - `CREATE TABLE tenants` per the plan spec.
  - `ALTER TABLE users ADD COLUMN tenant_id UUID REFERENCES tenants(id)`.
  - `ALTER TABLE clients, uploaded_files, ais_records, form26as_records, tax_computations, recommendations, audit_logs ADD COLUMN tenant_id UUID REFERENCES tenants(id)`.
  - Backfill: for every existing user create one tenant; set `users.tenant_id = tenants.id`; set every other row's `tenant_id` from `users.tenant_id` via owner_id join.
  - `NOT NULL` constraints added after backfill.
  - Indexes on `tenant_id` on every affected table.
- Update SQLAlchemy models in `backend/app/db/models.py`.
- Update JWT payload in `backend/app/core/security.py` to include `tid` and `rol`.
- New dependency `get_current_tenant()` in `backend/app/api/deps.py`.
- Refactor every repository in `backend/app/repositories.py` to filter by `tenant_id` not `owner_id`.
- Add registration flow: when a user registers, a tenant is auto-created with `legal_name = full_name`, `billing_email = email`, `place_of_supply_state_code = '07'` (Delhi default).
- New endpoints:
  - `GET  /api/v1/tenant`  — current tenant detail
  - `PATCH /api/v1/tenant` — update legal_name, trade_name, gstin, pan, place_of_supply_state_code, billing_address
- Frontend: `frontend/app/settings/firm/page.tsx` (firm details form).

### Phase 1B — Razorpay billing (GST-compliant)

- Alembic revision `0003_billing.py`: `plans`, `subscriptions`, `invoices`, `billing_events` per plan spec.
- Seed plans (idempotent seed script `backend/scripts/seed_plans.py`):
  - `STARTER` — ₹999/mo or ₹9,999/yr — limits: `clients=25, documents_month=200`
  - `PRO` — ₹2,499/mo or ₹24,999/yr — limits: `clients=150, documents_month=2000`
  - `FIRM` — ₹6,999/mo or ₹69,999/yr — limits: `clients=1000, documents_month=20000`
- `backend/app/services/razorpay_client.py` — thin async wrapper around `https://api.razorpay.com/v1` using `httpx`. Endpoints: `create_subscription`, `cancel_subscription`, `fetch_subscription`, `create_customer`, `fetch_invoice`.
- `backend/app/services/billing.py` — orchestrator: create subscription, sync subscription state, generate GST invoice PDF on `subscription.charged` webhook.
- `backend/app/services/invoice_pdf.py` — `reportlab`-based generator. Fields per CGST Rule 46:
  - Supplier legal_name + GSTIN + address + state code (from `BILLING_SUPPLIER_*` env)
  - Recipient legal_name + GSTIN + address + state code (from tenant)
  - Invoice number from FY series `{prefix}/{fy}/{sequence:05d}` (e.g. `APC/2026-27/00001`)
  - HSN/SAC `998314`
  - CGST 9% + SGST 9% if `tenants.place_of_supply_state_code == BILLING_SUPPLIER_STATE_CODE`; else IGST 18%.
  - Reverse-charge: "No".
  - "This is a computer-generated invoice" footer.
- `backend/app/api/billing.py`:
  ```
  GET    /api/v1/billing/plans
  POST   /api/v1/billing/subscriptions
  GET    /api/v1/billing/subscription
  POST   /api/v1/billing/subscriptions/cancel
  POST   /api/v1/billing/subscriptions/resume
  GET    /api/v1/billing/invoices
  GET    /api/v1/billing/invoices/{id}.pdf
  POST   /api/v1/billing/webhooks/razorpay
  ```
- Webhook handler must:
  - Read raw body + `X-Razorpay-Signature`; verify via `verify_razorpay(body, signature, RAZORPAY_WEBHOOK_SECRET)`.
  - Insert into `billing_events` with `provider_event_id` UNIQUE for idempotency.
  - Enqueue worker job `billing.process_event(event_id)`.
  - Return 200 within 5s regardless of downstream processing.
- Plan-gating dependency `enforce_plan_limit("clients" | "documents_month")` raising 402 with body `{"error":"plan_limit_exceeded","upgrade_url":"/billing/plans"}`.
- Frontend:
  - `frontend/app/billing/page.tsx` — current plan + usage meters.
  - `frontend/app/billing/plans/page.tsx` — plan picker; on select call backend then open Razorpay Checkout (`https://checkout.razorpay.com/v1/checkout.js`) using `NEXT_PUBLIC_RAZORPAY_KEY_ID`.
  - `frontend/app/billing/invoices/page.tsx` — list + download.
  - `frontend/components/billing/PlanGate.tsx` — wraps gated features; catches 402 and shows upgrade modal.
- Tests:
  - Invoice number generator is monotonic per FY and tenant.
  - CGST/SGST vs IGST routing based on POS.
  - Webhook signature verification accepts valid, rejects tampered.
  - Webhook idempotency: replaying the same event_id is a no-op.

### Phase 1C — Digio e-sign

- Alembic revision `0004_esign.py`: `esign_templates`, `esign_documents`, `esign_signatories` per plan spec.
- `backend/app/services/digio_client.py` — async httpx wrapper around Digio Sign API.
- `backend/app/services/esign.py` — orchestrator: render template → upload PDF to Digio → create signature request → poll/webhook → store signed PDF in S3 → update `esign_documents.status`.
- Endpoints:
  ```
  POST /api/v1/esign/templates
  GET  /api/v1/esign/templates
  POST /api/v1/esign/documents
  GET  /api/v1/esign/documents
  GET  /api/v1/esign/documents/{id}
  POST /api/v1/esign/documents/{id}/remind
  POST /api/v1/esign/documents/{id}/cancel
  GET  /api/v1/esign/documents/{id}/signed.pdf
  POST /api/v1/esign/webhooks/digio
  ```
- Webhook: HMAC verify via `verify_digio(...)`; idempotent on `digio_document_id + event_type`.
- Ship four default templates as seed data (`backend/scripts/seed_esign_templates.py`):
  1. `engagement_letter`
  2. `itr_efiling_consent`
  3. `ais_authorisation`
  4. `digilocker_consent`
- Use Jinja2 to render `body_md` with client + tenant + AY context, then convert MD → PDF via `markdown` + `weasyprint` (add to requirements). Stored unsigned PDF in S3 before sending to Digio.
- Frontend:
  - `frontend/app/clients/[id]/esign/page.tsx` — list documents for a client, "Send for signature" action.
  - `frontend/app/esign/page.tsx` — firm-wide dashboard.
  - `frontend/app/settings/templates/page.tsx` — template editor.

### Phase 1D — DigiLocker

- Alembic revision `0005_digilocker.py`: `digilocker_links`, `digilocker_documents` per plan spec. Token columns use `EncryptedString`.
- `backend/app/services/digilocker_client.py` — async httpx wrapper. PKCE for OAuth.
- Endpoints:
  ```
  POST   /api/v1/digilocker/links                       # CA creates link + invite
  GET    /api/v1/digilocker/links
  GET    /api/v1/digilocker/links/{id}
  DELETE /api/v1/digilocker/links/{id}                  # revoke + purge fetched docs
  GET    /api/v1/digilocker/oauth/{link_id}/start       # client-facing redirect
  GET    /api/v1/digilocker/callback                    # OAuth callback
  POST   /api/v1/digilocker/links/{id}/sync             # pull issued docs list
  POST   /api/v1/digilocker/links/{id}/fetch            # fetch a specific URI -> uploaded_files
  ```
- Worker job `digilocker.sync(link_id)` pulls issued documents and persists. If a doc is `FORM16`, automatically enqueue a follow-up `ais.parse(uploaded_file_id)` job.
- **Hard-code the user-facing warning** that AIS / 26AS / TIS are not currently fetched via DigiLocker; they remain manual upload until ITDREIN access is arranged. Surface this warning on the DigiLocker invite UI and inside the API response payload (`unsupported_doc_types: ["AIS","26AS","TIS"]`).
- Frontend:
  - `frontend/app/clients/[id]/digilocker/page.tsx` — invite + sync UI.
  - `frontend/app/digilocker/page.tsx` — firm-wide list of links.

### Phase 1E — WhatsApp Business API (Meta Cloud API direct)

- Alembic revision `0006_whatsapp.py`: `whatsapp_templates`, `whatsapp_consents`, `whatsapp_messages` per plan spec.
- `backend/app/services/whatsapp_client.py` — async httpx wrapper around `https://graph.facebook.com/{META_API_VERSION}/{META_PHONE_NUMBER_ID}/messages`.
- Endpoints:
  ```
  POST /api/v1/whatsapp/templates
  GET  /api/v1/whatsapp/templates
  POST /api/v1/whatsapp/messages
  GET  /api/v1/whatsapp/conversations/{client_id}
  POST /api/v1/whatsapp/webhooks
  GET  /api/v1/whatsapp/webhooks                        # Meta verify-token handshake
  POST /api/v1/whatsapp/consents/opt-in
  POST /api/v1/whatsapp/consents/opt-out
  ```
- Outbound send must (a) require an `APPROVED` template if outside 24-hour customer-service window; (b) check `whatsapp_consents` row exists and `opted_out_at IS NULL`; (c) enqueue `whatsapp.send(message_id)` worker job.
- Webhook handler: verify via `verify_meta(body, signature, META_APP_SECRET)`; handle `messages`, `statuses`, `messaging_postbacks`; idempotent on `wa_message_id`.
- Seed six default templates with `status=PENDING` and a script `backend/scripts/submit_whatsapp_templates.py` to submit them to Meta when credentials are configured:
  1. `tax_filing_reminder_v1`
  2. `document_request_v1`
  3. `digilocker_invite_v1`
  4. `itr_acknowledgement_v1`
  5. `invoice_reminder_v1`
  6. `otp_login_v1`
- Frontend:
  - `frontend/app/clients/[id]/messages/page.tsx` — conversation view + template picker.
  - `frontend/app/templates/page.tsx` — list templates + their Meta approval status.

### Phase 1F — production deployment

- Add `Procfile`-style configuration (Railway uses `railway.toml`):
  - `backend` service: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'`
  - `worker` service: `arq backend.app.worker.WorkerSettings`
- Update `backend/app/core/config.py` to support `BASE_URL` env var and use it in webhook callback URL generation.
- Update `frontend/vercel.json` to add `regions: ["bom1"]` for Mumbai edge.
- Update `frontend/.env.example` with `NEXT_PUBLIC_API_URL=https://api.associatepiyush.in` and `NEXT_PUBLIC_RAZORPAY_KEY_ID=`.
- Update `backend/.env.example` `CORS_ORIGINS=https://app.associatepiyush.in,http://localhost:3000`.
- Write `docs/RUNBOOK.md` covering: DNS records to create (CNAME `app` → `cname.vercel-dns.com`, CNAME `api` → Railway target), Railway custom-domain steps, Vercel custom-domain steps, webhook URL updates in each provider dashboard, smoke-test checklist, rollback procedure.
- Write `docs/SECRETS.md` covering rotation runbooks for every secret in `.env.example`.

### Phase 1G — hardening sweep

- Add `backend/app/api/middleware/audit.py` that writes every authenticated `POST/PATCH/DELETE` to `audit_logs` with redacted body.
- Add a nightly worker job `backups.pg_dump_to_s3()` (cron via ARQ cron jobs) — daily at 02:00 IST, 30-day retention.
- Add `/ready` endpoint that checks DB + Redis + S3 connectivity.
- Run `pytest --cov` and report coverage; raise to ≥ 75% on every new module.
- Run `ruff check . --fix` and `mypy backend/` and resolve issues.
- Write `docs/COMPLIANCE.md` covering: DPDPA notice template, grievance officer contact, processor list (Razorpay, Digio, Meta, DigiLocker, OpenAI, AWS), retention schedule, data subject rights flow.

## Sensible defaults (override only if the founder objects)

| Setting | Default |
|---|---|
| Billing supplier legal name | `Associate Piyush & Co.` |
| Billing supplier trade name | `AssociatePiyush` |
| Billing supplier GSTIN | `__SET_BEFORE_GO_LIVE__` (placeholder; invoice generator refuses to generate until set) |
| Billing supplier state code | `07` (Delhi) |
| Invoice prefix | `APC` |
| HSN/SAC | `998314` |
| GST rates | CGST 9% + SGST 9% intra-state; IGST 18% inter-state |
| Plan pricing | Starter ₹999/mo · Pro ₹2,499/mo · Firm ₹6,999/mo (annual = 10× monthly) |
| Plan limits | Starter 25/200 · Pro 150/2 000 · Firm 1 000/20 000 (clients / documents-per-month) |
| Postgres region | `ap-south-1` (Mumbai) |
| Object storage | AWS S3 `ap-south-1`; MinIO for local dev |
| Default Digio expiry | 30 days |
| Meta API version | `v22.0` |
| Retention | 8 years (ICAI); soft-delete with `deleted_at`; hard-delete via worker after window |
| Background worker | ARQ over Redis 7 |
| Frontend region | Vercel `bom1` |

## Working agreement

1. Read all files listed at the top before writing code.
2. Do not skip Phase 0 — every later phase depends on Alembic, S3, Redis, encryption helpers, and webhook helpers.
3. Pause and summarise after each phase. Wait for me to type `continue` before starting the next phase.
4. Never modify `database/schema.sql` by hand — always go through Alembic and regenerate.
5. Never commit real secrets. Use placeholders in `.env.example`.
6. If a provider's official Python SDK exists and is maintained (Razorpay has one; Digio has one), prefer the SDK over hand-rolled httpx calls — but still keep the wrapper under `backend/app/services/<provider>_client.py` so tests can mock at a single seam.
7. If you encounter ambiguity that the plan does not resolve, prefer the safer / more compliant choice and call it out in the phase-summary message.
8. Every Alembic migration must be reversible (`downgrade()` implemented). Every new table must have `tenant_id` (where applicable) indexed.
9. Every webhook handler must respond 2xx within 5 seconds; long work goes to the worker.
10. Frontend components must be accessible (semantic HTML, labels, focus management) and responsive (mobile breakpoint 640px and up).

Start with Phase 0 now. After Phase 0 is complete with tests green, summarise what changed and wait for `continue`.

---PROMPT END---

## How to use this prompt

1. Open Claude Code in the repo root.
2. Paste the block between the markers above as your first message.
3. Claude Code will read the design spec (`docs/PHASE_1_PRODUCTIONISATION_PLAN.md`) and the existing code, then begin Phase 0.
4. After each phase, review the diff and type `continue` to proceed to the next phase, or give targeted feedback before continuing.
5. Provider credentials (Razorpay, Digio, DigiLocker, Meta) can be added to `backend/.env` at any point; the integration code is written to gracefully degrade when they are absent (returns 503 with `provider_not_configured`).

## Critical placeholders to fill before go-live

- `BILLING_SUPPLIER_GSTIN` — your CA firm's GSTIN.
- `BILLING_SUPPLIER_ADDRESS_JSON` — registered address.
- `BILLING_SUPPLIER_STATE_CODE` — if not Delhi (07), update.
- All provider API keys (Razorpay live, Digio prod, DigiLocker partner, Meta WABA).
