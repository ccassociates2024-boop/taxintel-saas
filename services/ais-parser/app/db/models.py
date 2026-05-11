import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AisImport(Base):
    __tablename__ = "ais_imports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_year: Mapped[str] = mapped_column(String(16), nullable=False)
    source_file_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PARSED")
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    transactions: Mapped[list["AisTransaction"]] = relationship(
        back_populates="ais_import", cascade="all, delete-orphan"
    )
    mismatches: Mapped[list["AisMismatch"]] = relationship(
        back_populates="ais_import", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "client_id", "assessment_year", "source_file_hash"),
        Index("ix_ais_imports_tenant_client_ay", "tenant_id", "client_id", "assessment_year"),
    )


class AisTransaction(Base):
    __tablename__ = "ais_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ais_imports.id"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_year: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    information_code: Mapped[str | None] = mapped_column(String(32))
    source_name: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    transaction_date: Mapped[date | None] = mapped_column(Date)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    ais_import: Mapped[AisImport] = relationship(back_populates="transactions")

    __table_args__ = (
        Index("ix_ais_txn_tenant_client_ay_category", "tenant_id", "client_id", "assessment_year", "category"),
    )


class AisMismatch(Base):
    __tablename__ = "ais_mismatches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ais_imports.id"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_year: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    ais_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    declared_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    difference: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    ais_import: Mapped[AisImport] = relationship(back_populates="mismatches")

