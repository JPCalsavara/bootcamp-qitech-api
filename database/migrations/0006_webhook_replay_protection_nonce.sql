-- ==============================================================================
-- Migration: 0006_webhook_replay_protection_nonce.sql
-- Domínio: Segurança de Webhook, Proteção contra Replay Attacks e Nonce
-- ==============================================================================

CREATE TABLE IF NOT EXISTS webhook_nonce(
    id                              SERIAL PRIMARY KEY,
    nonce                           VARCHAR(255) NOT NULL UNIQUE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE INDEX IF NOT EXISTS idx_webhook_nonce_created_at ON webhook_nonce(created_at);
