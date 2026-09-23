-- ==============================================================================
-- Migration: 0003_pockets_and_governance.sql
-- Domínio: Caixinhas de Governança, Políticas de Transferência e Teto MEI (RFC 03, RFC 04)
-- ==============================================================================

-- RFC 07 / RFC 03: Pockets & Governança Patrimonial
CREATE TABLE IF NOT EXISTS pocket_type(
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

CREATE TABLE IF NOT EXISTS pocket(
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

CREATE TABLE IF NOT EXISTS transfer_policy(
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

CREATE TABLE IF NOT EXISTS revenue_tracker(
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
