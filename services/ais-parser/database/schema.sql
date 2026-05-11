CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS ais_imports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    client_id UUID NOT NULL,
    assessment_year VARCHAR(16) NOT NULL,
    source_file_name TEXT NOT NULL,
    source_file_hash VARCHAR(64) NOT NULL,
    parser_version VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PARSED',
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, client_id, assessment_year, source_file_hash)
);

CREATE INDEX IF NOT EXISTS ix_ais_imports_tenant_client_ay
ON ais_imports (tenant_id, client_id, assessment_year);

CREATE TABLE IF NOT EXISTS ais_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    import_id UUID NOT NULL REFERENCES ais_imports(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    client_id UUID NOT NULL,
    assessment_year VARCHAR(16) NOT NULL,
    category VARCHAR(64) NOT NULL,
    information_code VARCHAR(32),
    source_name TEXT,
    amount NUMERIC(14, 2) NOT NULL,
    transaction_date DATE,
    confidence NUMERIC(5, 4) NOT NULL,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_ais_txn_tenant_client_ay_category
ON ais_transactions (tenant_id, client_id, assessment_year, category);

CREATE TABLE IF NOT EXISTS ais_mismatches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    import_id UUID NOT NULL REFERENCES ais_imports(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    client_id UUID NOT NULL,
    assessment_year VARCHAR(16) NOT NULL,
    category VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    ais_amount NUMERIC(14, 2) NOT NULL,
    declared_amount NUMERIC(14, 2) NOT NULL,
    difference NUMERIC(14, 2) NOT NULL,
    message TEXT NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

