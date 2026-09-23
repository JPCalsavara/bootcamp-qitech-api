-- ==============================================================================
-- Migration: 0004_charges_and_credit_ccb.sql
-- Domínio: Cobranças, Liquidação com Tarifa Atômica e Crédito CCB (RFC 02, RFC 04, ADR-0008)
-- ==============================================================================

-- RFC 04 / RFC 02: Meios de Pagamento & Cobrança
CREATE TABLE IF NOT EXISTS charge_method(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO charge_method (enumerator, description) VALUES
('PIX', 'Cobrança instantânea via PIX com QR Code dinâmico'),
('BOLETO', 'Boleto híbrido com código de barras e QR Code PIX'),
('CREDIT_CARD_LINK', 'Link de pagamento para cartão de crédito com antifraude')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS charge_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO charge_status (enumerator, description) VALUES
('created', 'Cobrança gerada e aguardando pagamento'),
('pending', 'Pagamento em processamento na câmara'),
('paid', 'Cobrança liquidada com sucesso'),
('expired', 'Cobrança expirada sem pagamento'),
('failed', 'Tentativa de liquidação falhou'),
('charged_back', 'Cobrança contestada pelo pagador')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS charge(
    id                              SERIAL PRIMARY KEY,
    charge_key                      CHAR(36) NOT NULL UNIQUE,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    method_id                       INTEGER NOT NULL REFERENCES charge_method(id),
    status_id                       INTEGER NOT NULL REFERENCES charge_status(id),
    amount                          BIGINT NOT NULL,
    fee_amount                      BIGINT NOT NULL DEFAULT 0,
    net_amount                      BIGINT NOT NULL,
    due_date                        DATE NOT NULL,
    qr_code                         TEXT,
    barcode                         VARCHAR(100),
    payment_url                     TEXT,
    customer_document               VARCHAR(20),
    metadata                        JSONB,
    paid_at                         TIMESTAMP,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS webhook_event(
    id                              SERIAL PRIMARY KEY,
    event_key                       CHAR(36) NOT NULL UNIQUE,
    event_type                      VARCHAR(100) NOT NULL,
    payload                         JSONB NOT NULL,
    signature                       VARCHAR(255) NOT NULL,
    processed                       BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at                    TIMESTAMP,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS chargeback_claim(
    id                              SERIAL PRIMARY KEY,
    claim_key                       CHAR(36) NOT NULL UNIQUE,
    charge_id                       INTEGER NOT NULL REFERENCES charge(id),
    amount                          BIGINT NOT NULL,
    reason                          VARCHAR(255) NOT NULL,
    status                          VARCHAR(50) NOT NULL DEFAULT 'OPEN',
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- RFC 05 / RFC 04: Linhas de Crédito & Trava de Recebíveis
CREATE TABLE IF NOT EXISTS credit_contract_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO credit_contract_status (enumerator, description) VALUES
('simulated', 'Proposta de crédito simulada'),
('approved', 'Proposta aprovada na esteira de risco'),
('disbursed', 'Crédito desembolsado na conta PJ'),
('active', 'Contrato ativo com parcelas em amortização'),
('settled', 'Contrato totalmente quitado'),
('defaulted', 'Contrato em inadimplência'),
('cancelled', 'Proposta cancelada')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS credit_contract(
    id                              SERIAL PRIMARY KEY,
    contract_key                    CHAR(36) NOT NULL UNIQUE,
    customer_id                     INTEGER NOT NULL REFERENCES customer(id),
    account_pj_id                   INTEGER NOT NULL REFERENCES account(id),
    account_pf_id                   INTEGER NOT NULL REFERENCES account(id),
    status_id                       INTEGER NOT NULL REFERENCES credit_contract_status(id),
    requested_amount                BIGINT NOT NULL,
    total_amount                    BIGINT NOT NULL,
    interest_rate_monthly           NUMERIC(5,4) NOT NULL,
    term_months                     INTEGER NOT NULL,
    retention_percentage            NUMERIC(5,2) NOT NULL,
    pocket_id                       INTEGER REFERENCES pocket(id),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS credit_installment(
    id                              SERIAL PRIMARY KEY,
    installment_key                 CHAR(36) NOT NULL UNIQUE,
    contract_id                     INTEGER NOT NULL REFERENCES credit_contract(id),
    installment_number              INTEGER NOT NULL,
    amount                          BIGINT NOT NULL,
    principal_amount                BIGINT NOT NULL,
    interest_amount                 BIGINT NOT NULL,
    due_date                        DATE NOT NULL,
    paid_amount                     BIGINT NOT NULL DEFAULT 0,
    status                          VARCHAR(50) NOT NULL DEFAULT 'OPEN',
    paid_at                         TIMESTAMP,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS receivables_anticipation(
    id                              SERIAL PRIMARY KEY,
    anticipation_key                CHAR(36) NOT NULL UNIQUE,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    original_amount                 BIGINT NOT NULL,
    discount_fee                    BIGINT NOT NULL,
    net_disbursed_amount            BIGINT NOT NULL,
    charge_ids                      JSONB NOT NULL,
    status                          VARCHAR(50) NOT NULL DEFAULT 'COMPLETED',
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);
