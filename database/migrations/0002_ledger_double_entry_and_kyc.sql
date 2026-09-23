-- ==============================================================================
-- Migration: 0002_ledger_double_entry_and_kyc.sql
-- Domínio: Transacional, Livro-Razão Imutável e KYC Antifraude (RFC 01, RFC 02, ADR-0004, ADR-0006)
-- ==============================================================================

-- RFC 02: Transactions & Double-Entry Ledger
CREATE TABLE IF NOT EXISTS transaction_type(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO transaction_type (enumerator, description) VALUES
('TRANSFER_INTERNAL', 'Transferência interna entre contas PF e PJ'),
('PIX_CASH_IN', 'Entrada de recursos via PIX'),
('PIX_CASH_OUT', 'Saída de recursos via PIX'),
('BOLETO_CASH_IN', 'Entrada de recursos via Boleto de Cobrança'),
('FEE_DEBIT', 'Débito atômico de taxa operacional / transacional'),
('CREDIT_DISBURSEMENT', 'Liberação de crédito CCB em conta PJ'),
('CREDIT_AMORTIZATION', 'Amortização de parcela de crédito'),
('RECEIVABLES_ANTICIPATION', 'Liquidação de antecipação de recebíveis'),
('TREASURY_YIELD', 'Crédito de rendimento automático CDB 100 por cento CDI'),
('CHARGEBACK_DEBIT', 'Débito por contestação de cobrança')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS transaction_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO transaction_status (enumerator, description) VALUES
('pending', 'Transação iniciada aguardando liquidação'),
('completed', 'Transação liquidada com sucesso no ledger'),
('failed', 'Transação falhou'),
('cancelled', 'Transação cancelada')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS transaction(
    id                              SERIAL PRIMARY KEY,
    transaction_key                 CHAR(36) NOT NULL UNIQUE,
    idempotency_key                 VARCHAR(255) UNIQUE,
    type_id                         INTEGER NOT NULL REFERENCES transaction_type(id),
    status_id                       INTEGER NOT NULL REFERENCES transaction_status(id),
    amount                          BIGINT NOT NULL,
    fee_amount                      BIGINT NOT NULL DEFAULT 0,
    source_account_id               INTEGER REFERENCES account(id),
    destination_account_id          INTEGER REFERENCES account(id),
    description                     VARCHAR(255),
    metadata                        JSONB,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS transaction_status_event(
    id                              SERIAL PRIMARY KEY,
    transaction_id                  INTEGER NOT NULL REFERENCES transaction(id),
    from_status_id                  INTEGER REFERENCES transaction_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES transaction_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS ledger_entry(
    id                              SERIAL PRIMARY KEY,
    entry_key                       CHAR(36) NOT NULL UNIQUE,
    transaction_id                  INTEGER NOT NULL REFERENCES transaction(id),
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    entry_type                      VARCHAR(10) NOT NULL CHECK (entry_type IN ('DEBIT', 'CREDIT')),
    amount                          BIGINT NOT NULL CHECK (amount > 0),
    balance_after                   BIGINT NOT NULL,
    description                     VARCHAR(255),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS idempotency_record(
    id                              SERIAL PRIMARY KEY,
    idempotency_key                 VARCHAR(255) NOT NULL UNIQUE,
    request_hash                    VARCHAR(64) NOT NULL,
    response_code                   INTEGER NOT NULL,
    response_body                   JSONB NOT NULL,
    expires_at                      TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- RFC 01 & RFC 03: KYC & Antifraude
CREATE TABLE IF NOT EXISTS kyc_risk_tier(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO kyc_risk_tier (enumerator, description) VALUES
('LOW', 'Baixo risco de crédito e fraude'),
('MEDIUM', 'Médio risco de crédito e fraude'),
('HIGH', 'Alto risco de crédito e fraude')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS kyc_analysis(
    id                              SERIAL PRIMARY KEY,
    analysis_key                    CHAR(36) NOT NULL UNIQUE,
    customer_id                     INTEGER NOT NULL REFERENCES customer(id),
    risk_tier_id                    INTEGER NOT NULL REFERENCES kyc_risk_tier(id),
    score                           INTEGER NOT NULL,
    cnd_federal_status              VARCHAR(50) NOT NULL,
    cnd_trabalhista_status          VARCHAR(50) NOT NULL,
    cadsan_status                   VARCHAR(50) NOT NULL,
    flags                           JSONB NOT NULL,
    recommendation                  VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);
