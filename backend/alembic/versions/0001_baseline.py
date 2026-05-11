"""Baseline — mirror existing schema.sql + Phase 0 idempotency_keys table.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-11

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("role", sa.String(24), nullable=False, server_default="CA"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(180), nullable=False),
        sa.Column("pan", sa.String(512), nullable=False),   # Fernet-encrypted PAN
        sa.Column("email", sa.String(512)),                  # Fernet-encrypted email
        sa.Column("phone", sa.String(512)),                  # Fernet-encrypted phone
        sa.Column("residential_status", sa.String(48), nullable=False, server_default="RESIDENT"),
        sa.Column("client_type", sa.String(48), nullable=False, server_default="INDIVIDUAL"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_clients_owner_id", "clients", ["owner_id"])
    op.create_index("ix_clients_pan", "clients", ["pan"])

    op.create_table(
        "uploaded_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_type", sa.String(48), nullable=False),
        sa.Column("original_name", sa.Text, nullable=False),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="UPLOADED"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_uploaded_files_owner_id", "uploaded_files", ["owner_id"])
    op.create_index("ix_uploaded_files_client_id", "uploaded_files", ["client_id"])
    op.create_index("ix_uploaded_files_file_hash", "uploaded_files", ["file_hash"])

    op.create_table(
        "ais_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploaded_files.id", ondelete="SET NULL")),
        sa.Column("assessment_year", sa.String(16), nullable=False),
        sa.Column("salary", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("interest_income", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("dividend_income", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("capital_gains", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tds_tcs", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("foreign_remittance", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("high_value_transactions", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("raw_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ais_records_client_ay", "ais_records", ["client_id", "assessment_year"])

    op.create_table(
        "form26as_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploaded_files.id", ondelete="SET NULL")),
        sa.Column("assessment_year", sa.String(16), nullable=False),
        sa.Column("salary_tds", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("non_salary_tds", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tcs", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("advance_tax_paid", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("mismatch_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("raw_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_form26as_records_client_ay", "form26as_records", ["client_id", "assessment_year"])

    op.create_table(
        "tax_computations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_year", sa.String(16), nullable=False),
        sa.Column("old_regime_tax", sa.Numeric(14, 2), nullable=False),
        sa.Column("new_regime_tax", sa.Numeric(14, 2), nullable=False),
        sa.Column("recommended_regime", sa.String(8), nullable=False),
        sa.Column("tax_payable", sa.Numeric(14, 2), nullable=False),
        sa.Column("refund_estimate", sa.Numeric(14, 2), nullable=False),
        sa.Column("health_score", sa.Integer, nullable=False, server_default="75"),
        sa.Column("computation_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tax_computations_client_ay", "tax_computations", ["client_id", "assessment_year"])

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_year", sa.String(16), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("estimated_savings", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_recommendations_client_ay", "recommendations", ["client_id", "assessment_year"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(96), nullable=False),
        sa.Column("entity_type", sa.String(64)),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("metadata_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_logs_owner_id", "audit_logs", ["owner_id"])

    # Phase 0 addition — idempotency keys for safe retries on all POST endpoints
    op.create_table(
        "idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("request_hash", sa.CHAR(64), nullable=False),
        sa.Column("response_status", sa.SmallInteger, nullable=False),
        sa.Column("response_body", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime, nullable=False),
    )
    # Partial unique index: when tenant_id IS NOT NULL, enforce (tenant_id, key) uniqueness.
    # For NULL tenant_id (pre-Phase-1A), enforce uniqueness on key alone.
    op.execute(
        "CREATE UNIQUE INDEX uq_idempotency_keys_tenant_key "
        "ON idempotency_keys (tenant_id, key) WHERE tenant_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_idempotency_keys_null_tenant_key "
        "ON idempotency_keys (key) WHERE tenant_id IS NULL"
    )
    op.create_index("ix_idempotency_keys_expires_at", "idempotency_keys", ["expires_at"])


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("audit_logs")
    op.drop_table("recommendations")
    op.drop_table("tax_computations")
    op.drop_table("form26as_records")
    op.drop_table("ais_records")
    op.drop_table("uploaded_files")
    op.drop_table("clients")
    op.drop_table("users")
