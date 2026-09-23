-- ==============================================================================
-- Migration: 0001_initial_core_identity.sql
-- Domínio: Identidade, Onboarding e Contas Gêmeas PF/PJ (RFC 01, ADR-0005, ADR-0007)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS sample_entity_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO sample_entity_status (enumerator) VALUES
('created'),
('pending'),
('success'),
('failed')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS sample_entity(
    id                              SERIAL PRIMARY KEY,
    sample_entity_key               CHAR(36) NOT NULL UNIQUE,
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    sample_entity_data              JSONB NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL UNIQUE,
    document_number                 CHAR(14) NOT NULL UNIQUE,
    birthdate                       DATE NOT NULL,
    counter                         INTEGER NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS sample_entity_status_event(
    id                              SERIAL PRIMARY KEY,
    sample_entity_id                INTEGER NOT NULL REFERENCES sample_entity(id),
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- RFC 01 & RFC 03: Customer & Status
CREATE TABLE IF NOT EXISTS customer_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO customer_status (enumerator, description) VALUES
('created', 'Cadastro recebido, aguardando início de validações'),
('kyc_pending', 'Validações cadastrais e antifraude em andamento'),
('under_review', 'Cadastro sob análise manual de compliance'),
('active', 'Cadastro aprovado e contas ativas'),
('rejected', 'Cadastro recusado por fraude ou inconsistência grave'),
('blocked', 'Cadastro bloqueado cautelarmente por conformidade')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS customer(
    id                              SERIAL PRIMARY KEY,
    customer_key                    CHAR(36) NOT NULL UNIQUE,
    status_id                       INTEGER NOT NULL REFERENCES customer_status(id),
    name                            VARCHAR(255) NOT NULL,
    legal_name                      VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL UNIQUE,
    cpf                             CHAR(14) NOT NULL UNIQUE,
    cnpj                            CHAR(18) NOT NULL UNIQUE,
    birthdate                       DATE NOT NULL,
    phone                           VARCHAR(20) NOT NULL,
    password_hash                   VARCHAR(255) NOT NULL,
    pin_hash                        VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS customer_status_event(
    id                              SERIAL PRIMARY KEY,
    customer_id                     INTEGER NOT NULL REFERENCES customer(id),
    from_status_id                  INTEGER REFERENCES customer_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES customer_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    reason_detail                   JSONB,
    event_datetime                  TIMESTAMP NOT NULL DEFAULT(NOW()),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- RFC 01: Account Types & Status (Contas Gêmeas e Máquina de Estados)
CREATE TABLE IF NOT EXISTS account_type(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO account_type (enumerator, description) VALUES
('PF', 'Conta Pessoa Física associada ao titular MEI'),
('PJ', 'Conta Pessoa Jurídica da empresa MEI')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS account_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO account_status (enumerator, description) VALUES
('active', 'Conta ativa e operando normalmente'),
('blocked', 'Conta bloqueada para movimentações'),
('closed', 'Conta encerrada')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS account(
    id                              SERIAL PRIMARY KEY,
    account_key                     CHAR(36) NOT NULL UNIQUE,
    customer_id                     INTEGER NOT NULL REFERENCES customer(id),
    type_id                         INTEGER NOT NULL REFERENCES account_type(id),
    status_id                       INTEGER NOT NULL REFERENCES account_status(id),
    branch_number                   VARCHAR(10) NOT NULL DEFAULT '0001',
    account_number                  VARCHAR(20) NOT NULL UNIQUE,
    balance                         BIGINT NOT NULL DEFAULT 0,
    blocked_balance                 BIGINT NOT NULL DEFAULT 0,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(customer_id, type_id)
);

CREATE TABLE IF NOT EXISTS account_status_event(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    from_status_id                  INTEGER REFERENCES account_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES account_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);
