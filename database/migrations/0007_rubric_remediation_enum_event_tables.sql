-- ==============================================================================
-- Migration: 0007_rubric_remediation_enum_event_tables.sql
-- Domínio: Normalização de enums (COD-06), histórico append-only de status
--          (COD-07, ADR-0007) e chave pública de nonce de webhook (COD-05, ADR-0005)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- COD-06: Tabelas auxiliares de enum (mesma forma de charge_status/account_status)
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ledger_entry_type(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO ledger_entry_type (enumerator, description) VALUES
('DEBIT', 'Lançamento de débito no ledger'),
('CREDIT', 'Lançamento de crédito no ledger')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS kyc_cnd_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO kyc_cnd_status (enumerator, description) VALUES
('REGULAR', 'Situação cadastral regular'),
('IRREGULAR', 'Situação cadastral irregular'),
('PENDING', 'Situação cadastral pendente de verificação')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS webhook_event_type(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO webhook_event_type (enumerator, description) VALUES
('payment.settled', 'Liquidação de pagamento confirmada pelo parceiro')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS chargeback_claim_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO chargeback_claim_status (enumerator, description) VALUES
('OPEN', 'Contestação aberta aguardando análise')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS credit_installment_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO credit_installment_status (enumerator, description) VALUES
('OPEN', 'Parcela em aberto aguardando pagamento'),
('OVERDUE', 'Parcela vencida e inadimplente'),
('PAID', 'Parcela quitada')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE IF NOT EXISTS receivables_anticipation_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO receivables_anticipation_status (enumerator, description) VALUES
('COMPLETED', 'Antecipação liquidada e desembolsada')
ON CONFLICT (enumerator) DO NOTHING;

-- ------------------------------------------------------------------------------
-- COD-06: Troca das 8 colunas varchar/CHECK por <col>_id FK
-- (idempotente: só altera se a coluna legada ainda existir)
-- ------------------------------------------------------------------------------

-- ledger_entry.entry_type -> entry_type_id
ALTER TABLE ledger_entry ADD COLUMN IF NOT EXISTS entry_type_id INTEGER REFERENCES ledger_entry_type(id);
UPDATE ledger_entry e SET entry_type_id = t.id
    FROM ledger_entry_type t
    WHERE e.entry_type_id IS NULL
      AND EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'ledger_entry' AND column_name = 'entry_type')
      AND t.enumerator = e.entry_type;
ALTER TABLE ledger_entry ALTER COLUMN entry_type_id SET NOT NULL;
ALTER TABLE ledger_entry DROP COLUMN IF EXISTS entry_type;

-- kyc_analysis cnd/cadsan columns -> *_id
ALTER TABLE kyc_analysis ADD COLUMN IF NOT EXISTS cnd_federal_status_id INTEGER REFERENCES kyc_cnd_status(id);
ALTER TABLE kyc_analysis ADD COLUMN IF NOT EXISTS cnd_trabalhista_status_id INTEGER REFERENCES kyc_cnd_status(id);
ALTER TABLE kyc_analysis ADD COLUMN IF NOT EXISTS cadsan_status_id INTEGER REFERENCES kyc_cnd_status(id);
UPDATE kyc_analysis a SET cnd_federal_status_id = s.id
    FROM kyc_cnd_status s
    WHERE a.cnd_federal_status_id IS NULL
      AND EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'kyc_analysis' AND column_name = 'cnd_federal_status')
      AND s.enumerator = a.cnd_federal_status;
UPDATE kyc_analysis a SET cnd_trabalhista_status_id = s.id
    FROM kyc_cnd_status s
    WHERE a.cnd_trabalhista_status_id IS NULL
      AND EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'kyc_analysis' AND column_name = 'cnd_trabalhista_status')
      AND s.enumerator = a.cnd_trabalhista_status;
UPDATE kyc_analysis a SET cadsan_status_id = s.id
    FROM kyc_cnd_status s
    WHERE a.cadsan_status_id IS NULL
      AND EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'kyc_analysis' AND column_name = 'cadsan_status')
      AND s.enumerator = a.cadsan_status;
ALTER TABLE kyc_analysis ALTER COLUMN cnd_federal_status_id SET NOT NULL;
ALTER TABLE kyc_analysis ALTER COLUMN cnd_trabalhista_status_id SET NOT NULL;
ALTER TABLE kyc_analysis ALTER COLUMN cadsan_status_id SET NOT NULL;
ALTER TABLE kyc_analysis DROP COLUMN IF EXISTS cnd_federal_status;
ALTER TABLE kyc_analysis DROP COLUMN IF EXISTS cnd_trabalhista_status;
ALTER TABLE kyc_analysis DROP COLUMN IF EXISTS cadsan_status;

-- webhook_event.event_type -> event_type_id
ALTER TABLE webhook_event ADD COLUMN IF NOT EXISTS event_type_id INTEGER REFERENCES webhook_event_type(id);
UPDATE webhook_event w SET event_type_id = t.id
    FROM webhook_event_type t
    WHERE w.event_type_id IS NULL
      AND EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'webhook_event' AND column_name = 'event_type')
      AND t.enumerator = w.event_type;
ALTER TABLE webhook_event ALTER COLUMN event_type_id SET NOT NULL;
ALTER TABLE webhook_event DROP COLUMN IF EXISTS event_type;

-- chargeback_claim.status -> status_id
ALTER TABLE chargeback_claim ADD COLUMN IF NOT EXISTS status_id INTEGER REFERENCES chargeback_claim_status(id);
UPDATE chargeback_claim c SET status_id = s.id
    FROM chargeback_claim_status s
    WHERE c.status_id IS NULL
      AND EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'chargeback_claim' AND column_name = 'status')
      AND s.enumerator = c.status;
ALTER TABLE chargeback_claim ALTER COLUMN status_id SET NOT NULL;
ALTER TABLE chargeback_claim DROP COLUMN IF EXISTS status;

-- credit_installment.status -> status_id
ALTER TABLE credit_installment ADD COLUMN IF NOT EXISTS status_id INTEGER REFERENCES credit_installment_status(id);
UPDATE credit_installment i SET status_id = s.id
    FROM credit_installment_status s
    WHERE i.status_id IS NULL
      AND EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'credit_installment' AND column_name = 'status')
      AND s.enumerator = i.status;
ALTER TABLE credit_installment ALTER COLUMN status_id SET NOT NULL;
ALTER TABLE credit_installment DROP COLUMN IF EXISTS status;

-- receivables_anticipation.status -> status_id
ALTER TABLE receivables_anticipation ADD COLUMN IF NOT EXISTS status_id INTEGER REFERENCES receivables_anticipation_status(id);
UPDATE receivables_anticipation r SET status_id = s.id
    FROM receivables_anticipation_status s
    WHERE r.status_id IS NULL
      AND EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'receivables_anticipation' AND column_name = 'status')
      AND s.enumerator = r.status;
ALTER TABLE receivables_anticipation ALTER COLUMN status_id SET NOT NULL;
ALTER TABLE receivables_anticipation DROP COLUMN IF EXISTS status;

-- ------------------------------------------------------------------------------
-- COD-07: Tabelas de histórico append-only (mesma forma de account_status_event)
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS charge_status_event(
    id                              SERIAL PRIMARY KEY,
    charge_id                       INTEGER NOT NULL REFERENCES charge(id),
    from_status_id                  INTEGER REFERENCES charge_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES charge_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS chargeback_claim_status_event(
    id                              SERIAL PRIMARY KEY,
    chargeback_claim_id             INTEGER NOT NULL REFERENCES chargeback_claim(id),
    from_status_id                  INTEGER REFERENCES chargeback_claim_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES chargeback_claim_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS credit_contract_status_event(
    id                              SERIAL PRIMARY KEY,
    credit_contract_id              INTEGER NOT NULL REFERENCES credit_contract(id),
    from_status_id                  INTEGER REFERENCES credit_contract_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES credit_contract_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS credit_installment_status_event(
    id                              SERIAL PRIMARY KEY,
    credit_installment_id           INTEGER NOT NULL REFERENCES credit_installment(id),
    from_status_id                  INTEGER REFERENCES credit_installment_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES credit_installment_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE IF NOT EXISTS receivables_anticipation_status_event(
    id                              SERIAL PRIMARY KEY,
    receivables_anticipation_id     INTEGER NOT NULL REFERENCES receivables_anticipation(id),
    from_status_id                  INTEGER REFERENCES receivables_anticipation_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES receivables_anticipation_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- NOTE (COD-07, kyc): kyc_analysis não possui status mutável de ciclo de vida.
-- Cada linha é uma análise append-only (recommendation é fixado na inserção) e a
-- trilha de auditoria da mudança de estado do cliente é customer_status_event.
-- Portanto nenhuma tabela kyc_analysis_status_event é necessária.

-- ------------------------------------------------------------------------------
-- COD-05: chave pública de nonce de webhook (ADR-0005)
-- ------------------------------------------------------------------------------

ALTER TABLE webhook_nonce ADD COLUMN IF NOT EXISTS webhook_nonce_key CHAR(36);
UPDATE webhook_nonce SET webhook_nonce_key = gen_random_uuid()::text WHERE webhook_nonce_key IS NULL;
ALTER TABLE webhook_nonce ALTER COLUMN webhook_nonce_key SET NOT NULL;
ALTER TABLE webhook_nonce ADD CONSTRAINT webhook_nonce_webhook_nonce_key_key UNIQUE (webhook_nonce_key);
