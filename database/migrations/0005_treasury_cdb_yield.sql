-- ==============================================================================
-- Migration: 0005_treasury_cdb_yield.sql
-- Domínio: Tesouraria, Rendimento Diário CDI e Cash Sweep Invisível (RFC 03)
-- ==============================================================================

-- RFC 06 / RFC 03: Tesouraria & Fluxo Remunerado (CDB 100% CDI)
CREATE TABLE IF NOT EXISTS yield_position(
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

CREATE TABLE IF NOT EXISTS yield_accrual_event(
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
