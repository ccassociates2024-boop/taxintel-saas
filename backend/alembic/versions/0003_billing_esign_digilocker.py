"""Phase 1B-1D — subscriptions, invoices, esign_requests, digilocker_tokens.

Revision ID: 0003_billing_esign_digilocker
Revises: 0002_tenants
Create Date: 2026-05-11
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_billing_esign_digilocker"
down_revision: Union[str, None] = "0002_tenants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── subscriptions ─────────────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("razorpay_subscription_id", sa.String(64), unique=True),
        sa.Column("plan", sa.String(32), nullable=False, server_default="FREE"),
        sa.Column("status", sa.String(32), nullable=False, server_default="created"),
        sa.Column("current_period_start", sa.DateTime),
        sa.Column("current_period_end", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"])

    # ── invoices ──────────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_number", sa.String(32), nullable=False, unique=True),
        sa.Column("amount_subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("cgst", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("sgst", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("igst", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("amount_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("line_items", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("pdf_s3_key", sa.Text),
        sa.Column("razorpay_payment_id", sa.String(64)),
        sa.Column("period_start", sa.DateTime),
        sa.Column("period_end", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"])

    # ── esign_requests ────────────────────────────────────────────────────────
    op.create_table(
        "esign_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("digio_document_id", sa.String(64)),
        sa.Column("template_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("signer_email", sa.String(255), nullable=False),
        sa.Column("document_s3_key", sa.Text),
        sa.Column("signed_document_s3_key", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime),
    )
    op.create_index("ix_esign_requests_tenant_id", "esign_requests", ["tenant_id"])
    op.create_index("ix_esign_requests_client_id", "esign_requests", ["client_id"])

    # ── digilocker_tokens ─────────────────────────────────────────────────────
    op.create_table(
        "digilocker_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("access_token", sa.Text, nullable=False),
        sa.Column("refresh_token", sa.Text),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_digilocker_tokens_tenant_id", "digilocker_tokens", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("digilocker_tokens")
    op.drop_table("esign_requests")
    op.drop_table("invoices")
    op.drop_table("subscriptions")
