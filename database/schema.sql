CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(160) NOT NULL,
    role VARCHAR(24) NOT NULL DEFAULT 'CA',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(180) NOT NULL,
    pan VARCHAR(10) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(32),
    residential_status VARCHAR(48) NOT NULL DEFAULT 'RESIDENT',
    client_type VARCHAR(48) NOT NULL DEFAULT 'INDIVIDUAL',
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_clients_owner_id ON clients(owner_id);
CREATE INDEX IF NOT EXISTS ix_clients_pan ON clients(pan);

CREATE TABLE IF NOT EXISTS uploaded_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    file_type VARCHAR(48) NOT NULL,
    original_name TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'UPLOADED',
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_uploaded_files_owner_id ON uploaded_files(owner_id);
CREATE INDEX IF NOT EXISTS ix_uploaded_files_client_id ON uploaded_files(client_id);
CREATE INDEX IF NOT EXISTS ix_uploaded_files_file_hash ON uploaded_files(file_hash);

CREATE TABLE IF NOT EXISTS ais_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    uploaded_file_id UUID REFERENCES uploaded_files(id) ON DELETE SET NULL,
    assessment_year VARCHAR(16) NOT NULL,
    salary NUMERIC(14,2) NOT NULL DEFAULT 0,
    interest_income NUMERIC(14,2) NOT NULL DEFAULT 0,
    dividend_income NUMERIC(14,2) NOT NULL DEFAULT 0,
    capital_gains NUMERIC(14,2) NOT NULL DEFAULT 0,
    tds_tcs NUMERIC(14,2) NOT NULL DEFAULT 0,
    foreign_remittance NUMERIC(14,2) NOT NULL DEFAULT 0,
    high_value_transactions NUMERIC(14,2) NOT NULL DEFAULT 0,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ais_records_client_ay ON ais_records(client_id, assessment_year);

CREATE TABLE IF NOT EXISTS form26as_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    uploaded_file_id UUID REFERENCES uploaded_files(id) ON DELETE SET NULL,
    assessment_year VARCHAR(16) NOT NULL,
    salary_tds NUMERIC(14,2) NOT NULL DEFAULT 0,
    non_salary_tds NUMERIC(14,2) NOT NULL DEFAULT 0,
    tcs NUMERIC(14,2) NOT NULL DEFAULT 0,
    advance_tax_paid NUMERIC(14,2) NOT NULL DEFAULT 0,
    mismatch_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_form26as_records_client_ay ON form26as_records(client_id, assessment_year);

CREATE TABLE IF NOT EXISTS tax_computations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    assessment_year VARCHAR(16) NOT NULL,
    old_regime_tax NUMERIC(14,2) NOT NULL,
    new_regime_tax NUMERIC(14,2) NOT NULL,
    recommended_regime VARCHAR(8) NOT NULL,
    tax_payable NUMERIC(14,2) NOT NULL,
    refund_estimate NUMERIC(14,2) NOT NULL,
    health_score INTEGER NOT NULL DEFAULT 75,
    computation_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_tax_computations_client_ay ON tax_computations(client_id, assessment_year);

CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    assessment_year VARCHAR(16) NOT NULL,
    title TEXT NOT NULL,
    category VARCHAR(64) NOT NULL,
    priority VARCHAR(16) NOT NULL,
    estimated_savings NUMERIC(14,2) NOT NULL DEFAULT 0,
    summary TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_recommendations_client_ay ON recommendations(client_id, assessment_year);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(96) NOT NULL,
    entity_type VARCHAR(64),
    entity_id VARCHAR(64),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_owner_id ON audit_logs(owner_id);

