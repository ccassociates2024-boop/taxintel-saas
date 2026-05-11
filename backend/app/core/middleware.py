"""Cross-cutting Starlette middleware.

RequestIdMiddleware  — injects X-Request-Id into request state and response headers.
IdempotencyMiddleware — caches JSON responses keyed by Idempotency-Key header for 24h.

Notes
-----
- The idempotency store lives in the ``idempotency_keys`` table (see
  alembic/versions/0001_baseline.py).
- Only JSON (application/json) responses are cached; binary / streaming
  responses pass through unchanged.
- DB calls inside IdempotencyMiddleware use a thread-pool-executed sync
  session to avoid introducing an async session dependency at this layer.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


# ---------------------------------------------------------------------------
# RequestIdMiddleware
# ---------------------------------------------------------------------------

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id

        import structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


# ---------------------------------------------------------------------------
# IdempotencyMiddleware
# ---------------------------------------------------------------------------

_IDEMPOTENCY_TTL_HOURS = 24


def _check_cache(key: str, request_hash: str) -> dict | None:
    """Synchronous DB lookup — run in thread."""
    from sqlalchemy import select

    from app.db.models import IdempotencyKey
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        record = db.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.key == key,
                IdempotencyKey.request_hash == request_hash,
                IdempotencyKey.expires_at > datetime.utcnow(),
            )
        )
        if record:
            return {"status": record.response_status, "body": record.response_body}
        return None
    finally:
        db.close()


def _store_cache(key: str, request_hash: str, status: int, body: dict) -> None:
    """Synchronous DB write — run in thread."""
    from app.db.session import SessionLocal
    from app.db.models import IdempotencyKey

    db = SessionLocal()
    try:
        record = IdempotencyKey(
            key=key,
            request_hash=request_hash,
            response_status=status,
            response_body=body,
            expires_at=datetime.utcnow() + timedelta(hours=_IDEMPOTENCY_TTL_HOURS),
        )
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Replay idempotent responses for POST/PATCH requests with Idempotency-Key header."""

    async def dispatch(self, request: Request, call_next) -> Response:
        idempotency_key = request.headers.get("Idempotency-Key")

        if not idempotency_key or request.method not in {"POST", "PATCH", "PUT"}:
            return await call_next(request)

        # Read body bytes (caches them so the route handler can re-read)
        body_bytes = await request.body()
        request_hash = hashlib.sha256(
            f"{request.method}|{request.url.path}|{body_bytes.decode('utf-8', errors='replace')}".encode()
        ).hexdigest()

        # Check cache
        cached = await asyncio.to_thread(_check_cache, idempotency_key, request_hash)
        if cached:
            return JSONResponse(
                content=cached["body"],
                status_code=cached["status"],
                headers={"X-Idempotency-Replayed": "true"},
            )

        # Process request
        response = await call_next(request)

        # Only cache JSON responses (skip binary, streaming, errors from infrastructure)
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type and response.status_code < 500:
            # Drain the body iterator so we can cache and re-serve it
            raw_body = b""
            async for chunk in response.body_iterator:
                raw_body += chunk

            try:
                body_json = json.loads(raw_body)
            except Exception:
                body_json = {}

            await asyncio.to_thread(_store_cache, idempotency_key, request_hash, response.status_code, body_json)

            return Response(
                content=raw_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response
