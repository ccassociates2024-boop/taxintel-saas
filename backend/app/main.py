from __future__ import annotations

import os

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.api import (
    auth, billing, clients, dashboard, digilocker, esign,
    recommendations, reports, tax, tenant, uploads, whatsapp,
)
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import IdempotencyMiddleware, RequestIdMiddleware

# ── Logging must be configured before any other import that logs ───────────
configure_logging(
    log_level=settings.log_level,
    json_logs=settings.json_logs,
)

log = structlog.get_logger(__name__)

# ── Sentry — initialise only when DSN is present ──────────────────────────
if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    def _before_send(event, hint):
        for key in ("pan", "aadhaar", "access_token", "refresh_token", "otp"):
            if key in event.get("extra", {}):
                event["extra"][key] = "[REDACTED]"
        return event

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.05,
        before_send=_before_send,
        send_default_pii=False,
    )
    log.info("sentry.initialised", environment=settings.app_env)

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


def create_app() -> FastAPI:
    app = FastAPI(
        title="TaxIntel — Indian AI Tax Intelligence API",
        version="1.0.0",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
    )

    # ── Middleware (outermost → innermost) ──────────────────────────────────
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.limiter = limiter
    register_exception_handlers(app)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(_, __):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    # ── Probes ──────────────────────────────────────────────────────────────
    @app.get("/health", tags=["ops"])
    def health():
        return {"status": "ok", "version": "1.0.0"}

    @app.get("/ready", tags=["ops"])
    async def ready():
        failures: list[str] = []
        try:
            from app.db.session import engine
            import sqlalchemy as sa
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
        except Exception as exc:
            failures.append(f"db:{exc}")
        try:
            import redis as _redis
            r = _redis.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
        except Exception as exc:
            failures.append(f"redis:{exc}")
        try:
            from app.core import storage
            storage.object_exists("__healthcheck__")
        except Exception as exc:
            failures.append(f"s3:{exc}")
        if failures:
            return JSONResponse(status_code=503, content={"status": "degraded", "failures": failures})
        return {"status": "ready"}

    # ── Routers ─────────────────────────────────────────────────────────────
    prefix = "/api/v1"
    app.include_router(auth.router,            prefix=prefix)
    app.include_router(tenant.router,          prefix=prefix)
    app.include_router(clients.router,         prefix=prefix)
    app.include_router(uploads.router,         prefix=prefix)
    app.include_router(tax.router,             prefix=prefix)
    app.include_router(recommendations.router, prefix=prefix)
    app.include_router(dashboard.router,       prefix=prefix)
    app.include_router(reports.router,         prefix=prefix)
    # Phase 1B
    app.include_router(billing.router,         prefix=prefix)
    # Phase 1C
    app.include_router(esign.router,           prefix=prefix)
    # Phase 1D
    app.include_router(digilocker.router,      prefix=prefix)
    # Phase 1E
    app.include_router(whatsapp.router,        prefix=prefix)

    log.info("app.created", env=settings.app_env)
    return app


app = create_app()
