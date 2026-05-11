"""Phase 1A — Add tenants table; add tenant_id FK to all data tables.

Revision ID: 0002_tenants
Revises: 0001_baseline
Create Date: 2026-05-11

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_tenants"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that get tenant_id NOT NULL after backfill
_STRICT_TABLES = [
    "clients",
    "uploaded_files",
    "ais_records",
    "form26as_records",
    "tax_computations",
    "recommendations",
]


def upgrade() -> None:
    # ── 1. Create tenants table ────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("legal_name", sa.String(200), nullable=False),
        sa.Column("trade_name", sa.String(200), nullable=False),
        sa.Column("gstin", sa.String(15)),
        sa.Column("pan", sa.Text),
        sa.Column("billing_email", sa.String(255), nullable=False),
        sa.Column("place_of_supply_state_code", sa.String(2), nullable=False, server_default="07"),
        sa.Column("plan", sa.String(32), nullable=False, server_default="FREE"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )

    # ── 2. Add tenant_id (nullable) to all data tables ─────────────────────
    op.add_column("users", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    for table in [*_STRICT_TABLES, "audit_logs"]:
        op.add_column(table, sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))

    # ── 3. FK constraints (deferrable so backfill can work) ────────────────
    op.create_foreign_key("fk_users_tenant_id", "users", "tenants", ["tenant_id"], ["id"])
    for table in [*_STRICT_TABLES, "audit_logs"]:
        op.create_foreign_key(
            f"fk_{table}_tenant_id", table, "tenants", ["tenant_id"], ["id"]
        )
    # Wire pre-existing idempotency_keys.tenant_id to tenants
    op.create_foreign_key(
        "fk_idempotency_keys_tenant_id",
        "idempotency_keys", "tenants", ["tenant_id"], ["id"],
    )

    # ── 4. Backfill: one tenant per user ───────────────────────────────────
    # Creates a tenant using the user's full_name and email, then links them.
    # The CTE returns (id, billing_email) so we can join back to users.
    op.execute("""
        WITH new_tenants AS (
            INSERT INTO tenants
                (id, legal_name, trade_name, billing_email,
                 place_of_supply_state_code, plan, is_active, created_at)
            SELECT
                uuid_generate_v4(), full_name, full_name, email,
                '07', 'FREE', true, now()
            FROM users
            RETURNING id, billing_email
        )
        UPDATE users
        SET tenant_id = new_tenants.id
        FROM new_tenants
        WHERE users.email = new_tenants.billing_email
    """)

    # Backfill data tables via owner_id → users.tenant_id
    for table in _STRICT_TABLES:
        op.execute(f"""
            UPDATE {table}
            SET tenant_id = u.tenant_id
            FROM users u
            WHERE {table}.owner_id = u.id
        """)  # noqa: S608

    # audit_logs.owner_id is nullable; rows with NULL owner_id get NULL tenant_id (kept nullable)
    op.execute("""
        UPDATE audit_logs
        SET tenant_id = u.tenant_id
        FROM users u
        WHERE audit_logs.owner_id = u.id
    """)

    # ── 5. NOT NULL enforcement (strict tables + users) ────────────────────
    op.alter_column("users", "tenant_id", nullable=False)
    for table in _STRICT_TABLES:
        op.alter_column(table, "tenant_id", nullable=False)

    # ── 6. Indexes ─────────────────────────────────────────────────────────
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    for table in [*_STRICT_TABLES, "audit_logs"]:
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def downgrade() -> None:
    # Drop FK on idempotency_keys first
    op.drop_constraint("fk_idempotency_keys_tenant_id", "idempotency_keys", type_="foreignkey")

    for table in [*_STRICT_TABLES, "audit_logs"]:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")

    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_column("users", "tenant_id")

    op.drop_table("tenants")
