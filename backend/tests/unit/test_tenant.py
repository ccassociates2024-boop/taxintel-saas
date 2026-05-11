"""Unit tests for Phase 1A — Tenant model, JWT claims, and tenant API endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security import create_access_token, decode_token


# ---------------------------------------------------------------------------
# JWT claim tests (security.py)
# ---------------------------------------------------------------------------

class TestJwtClaims:
    def _make_token(self, **kwargs):
        return create_access_token(
            subject=kwargs.get("subject", str(uuid.uuid4())),
            role=kwargs.get("role", "CA"),
            tenant_id=kwargs.get("tenant_id", str(uuid.uuid4())),
            tenant_name=kwargs.get("tenant_name", "Test Firm"),
        )

    def test_token_contains_tid(self):
        tid = str(uuid.uuid4())
        token = self._make_token(tenant_id=tid)
        payload = decode_token(token)
        assert payload is not None
        assert payload["tid"] == tid

    def test_token_contains_tnm(self):
        token = self._make_token(tenant_name="Gupta & Associates")
        payload = decode_token(token)
        assert payload["tnm"] == "Gupta & Associates"

    def test_token_contains_rol(self):
        token = self._make_token(role="ADMIN")
        payload = decode_token(token)
        assert payload["rol"] == "ADMIN"

    def test_token_contains_sub(self):
        uid = str(uuid.uuid4())
        token = self._make_token(subject=uid)
        payload = decode_token(token)
        assert payload["sub"] == uid

    def test_token_does_not_contain_legacy_role_key(self):
        token = self._make_token()
        payload = decode_token(token)
        # Old key was "role", new key is "rol"
        assert "role" not in payload
        assert "rol" in payload

    def test_invalid_token_returns_none(self):
        assert decode_token("not.a.valid.token") is None

    def test_tampered_token_returns_none(self):
        token = self._make_token()
        # Flip last character
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        assert decode_token(tampered) is None


# ---------------------------------------------------------------------------
# get_current_tenant dependency
# ---------------------------------------------------------------------------

def _build_tenant_app() -> FastAPI:
    app = FastAPI()

    from app.api.tenant import router as tenant_router
    app.include_router(tenant_router)

    return app


class TestGetCurrentTenant:
    def _token(self, tenant_id: str, tenant_name: str = "Test Firm") -> str:
        return create_access_token(
            subject=str(uuid.uuid4()),
            role="CA",
            tenant_id=tenant_id,
            tenant_name=tenant_name,
        )

    def test_missing_token_returns_401(self):
        app = _build_tenant_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/tenant")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self):
        app = _build_tenant_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/tenant", headers={"Authorization": "Bearer invalid"})
        assert response.status_code == 401

    def test_valid_token_with_inactive_tenant_returns_401(self):
        tid = str(uuid.uuid4())
        token = self._token(tid)
        app = _build_tenant_app()

        inactive_tenant = MagicMock()
        inactive_tenant.is_active = False

        mock_db = MagicMock()
        mock_db.get.return_value = inactive_tenant

        from app.api import deps
        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/tenant", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_valid_token_with_active_tenant_returns_200(self):
        tid = str(uuid.uuid4())
        token = self._token(tid, "Sharma & Co")
        app = _build_tenant_app()

        mock_tenant = MagicMock()
        mock_tenant.is_active = True
        mock_tenant.id = uuid.UUID(tid)
        mock_tenant.legal_name = "Sharma & Co"
        mock_tenant.trade_name = "Sharma & Co"
        mock_tenant.gstin = None
        mock_tenant.billing_email = "ca@sharma.in"
        mock_tenant.place_of_supply_state_code = "07"
        mock_tenant.plan = "FREE"

        mock_db = MagicMock()
        mock_db.get.return_value = mock_tenant

        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/tenant", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tid
        assert data["trade_name"] == "Sharma & Co"


# ---------------------------------------------------------------------------
# Tenant model importable and has expected attributes
# ---------------------------------------------------------------------------

class TestTenantModel:
    def test_tenant_model_importable(self):
        from app.db.models import Tenant
        assert Tenant is not None

    def test_tenant_has_required_columns(self):
        from app.db.models import Tenant
        columns = {c.key for c in Tenant.__table__.columns}
        assert "id" in columns
        assert "legal_name" in columns
        assert "trade_name" in columns
        assert "billing_email" in columns
        assert "plan" in columns
        assert "is_active" in columns
        assert "place_of_supply_state_code" in columns

    def test_user_model_has_tenant_id(self):
        from app.db.models import User
        columns = {c.key for c in User.__table__.columns}
        assert "tenant_id" in columns

    def test_client_model_has_tenant_id(self):
        from app.db.models import Client
        columns = {c.key for c in Client.__table__.columns}
        assert "tenant_id" in columns


# ---------------------------------------------------------------------------
# TenantRepository
# ---------------------------------------------------------------------------

class TestTenantRepository:
    def test_get_delegates_to_db_get(self):
        from app.repositories import TenantRepository

        mock_db = MagicMock()
        tid = uuid.uuid4()
        repo = TenantRepository(mock_db)
        repo.get(tid)
        mock_db.get.assert_called_once()

    def test_update_sets_fields(self):
        from app.repositories import TenantRepository
        from app.schemas import TenantUpdate

        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.trade_name = "Old Name"

        payload = TenantUpdate(trade_name="New Name")
        repo = TenantRepository(mock_db)
        repo.update(mock_tenant, payload)

        assert mock_tenant.trade_name == "New Name"
        mock_db.commit.assert_called_once()

    def test_update_ignores_none_fields(self):
        from app.repositories import TenantRepository
        from app.schemas import TenantUpdate

        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.legal_name = "Unchanged"

        # Only trade_name is set; legal_name should not be touched
        payload = TenantUpdate(trade_name="New Trade Name")
        repo = TenantRepository(mock_db)
        repo.update(mock_tenant, payload)

        # legal_name should not have been reassigned via setattr
        assert mock_tenant.legal_name == "Unchanged"

    def test_create_adds_to_db(self):
        from app.repositories import TenantRepository

        mock_db = MagicMock()
        repo = TenantRepository(mock_db)
        repo.create(
            legal_name="Test Firm",
            trade_name="Test Firm",
            billing_email="firm@test.in",
        )
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
