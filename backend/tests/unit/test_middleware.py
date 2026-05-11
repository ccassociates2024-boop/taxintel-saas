"""Unit tests for backend/app/core/middleware.py."""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request


def _build_test_app() -> FastAPI:
    app = FastAPI()

    from app.core.middleware import IdempotencyMiddleware, RequestIdMiddleware

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(IdempotencyMiddleware)

    @app.post("/echo")
    async def echo(request: Request):
        return await request.json()

    @app.get("/get")
    async def get_endpoint():
        return {"method": "GET"}

    return app


@pytest.fixture
def client():
    return TestClient(_build_test_app(), raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# RequestIdMiddleware
# ---------------------------------------------------------------------------

class TestRequestIdMiddleware:
    def test_request_id_added_to_response(self, client):
        response = client.get("/get")
        assert "x-request-id" in response.headers

    def test_incoming_request_id_echoed(self, client):
        response = client.get("/get", headers={"X-Request-Id": "my-custom-id"})
        assert response.headers["x-request-id"] == "my-custom-id"

    def test_new_uuid_generated_when_absent(self, client):
        r1 = client.get("/get")
        r2 = client.get("/get")
        # Both should have IDs but they should differ
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


# ---------------------------------------------------------------------------
# IdempotencyMiddleware
# ---------------------------------------------------------------------------

class TestIdempotencyMiddleware:
    def test_get_requests_not_cached(self, client):
        """GET requests bypass the idempotency middleware."""
        # No Idempotency-Key needed on GET — middleware should ignore
        response = client.get("/get", headers={"Idempotency-Key": "key-1"})
        assert response.status_code == 200
        assert "x-idempotency-replayed" not in response.headers

    def test_no_idempotency_key_passes_through(self, client):
        response = client.post("/echo", json={"hello": "world"})
        assert response.status_code == 200
        assert "x-idempotency-replayed" not in response.headers

    def test_replay_returns_cached_response(self):
        """When the DB returns a cached response, the middleware replays it."""
        app = _build_test_app()
        test_client = TestClient(app)

        cached = {"status": 200, "body": {"hello": "cached"}}

        with patch("app.core.middleware._check_cache", return_value=cached):
            response = test_client.post(
                "/echo",
                json={"hello": "world"},
                headers={"Idempotency-Key": "idem-key-1"},
            )

        assert response.status_code == 200
        assert response.json() == {"hello": "cached"}
        assert response.headers.get("x-idempotency-replayed") == "true"

    def test_cache_miss_stores_response(self):
        """On cache miss, the response is stored in the DB."""
        app = _build_test_app()
        test_client = TestClient(app)

        with patch("app.core.middleware._check_cache", return_value=None) as mock_check, \
             patch("app.core.middleware._store_cache") as mock_store:

            response = test_client.post(
                "/echo",
                json={"foo": "bar"},
                headers={"Idempotency-Key": "idem-key-2"},
            )

        assert response.status_code == 200
        mock_store.assert_called_once()
        args = mock_store.call_args[0]
        assert args[0] == "idem-key-2"  # key
        assert args[2] == 200           # status code
        assert args[3] == {"foo": "bar"}  # body

    def test_non_json_response_not_cached(self):
        """Binary/text responses bypass the idempotency cache store."""
        app = _build_test_app()

        @app.post("/binary")
        async def binary_endpoint():
            from starlette.responses import Response
            return Response(content=b"raw bytes", media_type="application/octet-stream")

        test_client = TestClient(app)

        with patch("app.core.middleware._check_cache", return_value=None), \
             patch("app.core.middleware._store_cache") as mock_store:

            response = test_client.post(
                "/binary",
                content=b"data",
                headers={"Idempotency-Key": "binary-key"},
            )

        assert response.status_code == 200
        # Non-JSON response should NOT be stored
        mock_store.assert_not_called()
