CREATE TABLE sample_entity_status(
    id		                        SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO sample_entity_status (enumerator) VALUES
('created'),
('pending'),
('success'),
('failed')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE sample_entity(
    id                              SERIAL PRIMARY KEY,
    sample_entity_key               CHAR(36) NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    sample_entity_data              JSONB NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    document_number                 CHAR(14) NOT NULL,
    birthdate                       DATE NOT NULL,
    counter                         INTEGER NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(sample_entity_key),
    UNIQUE(document_number),
    UNIQUE(email)
);

CREATE TABLE sample_entity_status_event(
    id                              SERIAL PRIMARY KEY,
    sample_entity_id                INTEGER NOT NULL REFERENCES sample_entity(id),
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- RFC 01 & RFC 03: Customer & Status
CREATE TABLE customer_status(
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

CREATE TABLE customer(
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

CREATE TABLE customer_status_event(
    id                              SERIAL PRIMARY KEY,
    customer_id                     INTEGER NOT NULL REFERENCES customer(id),
    from_status_id                  INTEGER REFERENCES customer_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES customer_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    reason_detail                   JSONB,
    event_datetime                  TIMESTAMP NOT NULL DEFAULT(NOW()),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- RFC 01: Account Types & Status
CREATE TABLE account_type(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO account_type (enumerator, description) VALUES
('PF', 'Conta Pessoa Física associada ao titular MEI'),
('PJ', 'Conta Pessoa Jurídica da empresa MEI')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE account_status(
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

CREATE TABLE account(
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

CREATE TABLE account_status_event(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    from_status_id                  INTEGER REFERENCES account_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES account_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- RFC 02: Transactions & Double-Entry Ledger
CREATE TABLE transaction_type(
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

CREATE TABLE transaction_status(
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

CREATE TABLE transaction(
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

CREATE TABLE transaction_status_event(
    id                              SERIAL PRIMARY KEY,
    transaction_id                  INTEGER NOT NULL REFERENCES transaction(id),
    from_status_id                  INTEGER REFERENCES transaction_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES transaction_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE ledger_entry(
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

CREATE TABLE idempotency_record(
    id                              SERIAL PRIMARY KEY,
    idempotency_key                 VARCHAR(255) NOT NULL UNIQUE,
    request_hash                    VARCHAR(64) NOT NULL,
    response_code                   INTEGER NOT NULL,
    response_body                   JSONB NOT NULL,
    expires_at                      TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- RFC 03: KYC & Antifraude
CREATE TABLE kyc_risk_tier(
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

CREATE TABLE kyc_analysis(
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

-- RFC 07: Pockets & Governança Patrimonial
CREATE TABLE pocket_type(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO pocket_type (enumerator, description) VALUES
('DAS_IMPOSTOS', 'Reserva prioritária para pagamento mensal do DAS-MEI'),
('RESERVA_EMERGENCIA', 'Reserva de emergência para contingências da empresa'),
('TRAVA_CREDITO', 'Retenção automática para amortização de operações de crédito'),
('PRO_LABORE', 'Reserva de pró-labore para distribuição de lucros à PF'),
('PERSONALIZADO', 'Caixinha com objetivo personalizado')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE pocket(
    id                              SERIAL PRIMARY KEY,
    pocket_key                      CHAR(36) NOT NULL UNIQUE,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    type_id                         INTEGER NOT NULL REFERENCES pocket_type(id),
    name                            VARCHAR(100) NOT NULL,
    target_amount                   BIGINT NOT NULL DEFAULT 0,
    current_balance                 BIGINT NOT NULL DEFAULT 0,
    is_locked                       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE transfer_policy(
    id                              SERIAL PRIMARY KEY,
    policy_key                      CHAR(36) NOT NULL UNIQUE,
    account_pj_id                   INTEGER NOT NULL REFERENCES account(id),
    account_pf_id                   INTEGER NOT NULL REFERENCES account(id),
    max_daily_transfer_amount       BIGINT NOT NULL,
    require_pro_labore_approval     BOOLEAN NOT NULL DEFAULT TRUE,
    das_reserved_check              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE revenue_tracker(
    id                              SERIAL PRIMARY KEY,
    tracker_key                     CHAR(36) NOT NULL UNIQUE,
    customer_id                     INTEGER NOT NULL REFERENCES customer(id),
    calendar_year                   INTEGER NOT NULL,
    accumulated_revenue             BIGINT NOT NULL DEFAULT 0,
    threshold_warning_sent          BOOLEAN NOT NULL DEFAULT FALSE,
    threshold_danger_sent           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(customer_id, calendar_year)
);

-- RFC 04: Meios de Pagamento & Cobrança
CREATE TABLE charge_method(
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

CREATE TABLE charge_status(
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

CREATE TABLE charge(
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

CREATE TABLE webhook_event(
    id                              SERIAL PRIMARY KEY,
    event_key                       CHAR(36) NOT NULL UNIQUE,
    event_type                      VARCHAR(100) NOT NULL,
    payload                         JSONB NOT NULL,
    signature                       VARCHAR(255) NOT NULL,
    processed                       BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at                    TIMESTAMP,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE chargeback_claim(
    id                              SERIAL PRIMARY KEY,
    claim_key                       CHAR(36) NOT NULL UNIQUE,
    charge_id                       INTEGER NOT NULL REFERENCES charge(id),
    amount                          BIGINT NOT NULL,
    reason                          VARCHAR(255) NOT NULL,
    status                          VARCHAR(50) NOT NULL DEFAULT 'OPEN',
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- RFC 05: Linhas de Crédito & Trava de Recebíveis
CREATE TABLE credit_contract_status(
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

CREATE TABLE credit_contract(
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

CREATE TABLE credit_installment(
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

CREATE TABLE receivables_anticipation(
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

-- RFC 06: Tesouraria & Fluxo Remunerado (CDB 100 por cento CDI)
CREATE TABLE yield_position(
    id                              SERIAL PRIMARY KEY,
    position_key                    CHAR(36) NOT NULL UNIQUE,
    account_id                      INTEGER NOT NULL REFERENCES account(id) UNIQUE,
    principal_amount                BIGINT NOT NULL DEFAULT 0,
    accumulated_yield               BIGINT NOT NULL DEFAULT 0,
    iof_amount                      BIGINT NOT NULL DEFAULT 0,
    ir_amount                       BIGINT NOT NULL DEFAULT 0,
    net_yield                       BIGINT NOT NULL DEFAULT 0,
    last_accrual_date               DATE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE yield_accrual_event(
    id                              SERIAL PRIMARY KEY,
    event_key                       CHAR(36) NOT NULL UNIQUE,
    position_id                     INTEGER NOT NULL REFERENCES yield_position(id),
    date                            DATE NOT NULL,
    cdi_daily_rate                  NUMERIC(8,6) NOT NULL,
    gross_yield                     BIGINT NOT NULL,
    iof_withheld                    BIGINT NOT NULL,
    ir_withheld                     BIGINT NOT NULL,
    net_yield                       BIGINT NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);