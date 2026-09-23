# Histórico de Migrações do Banco de Dados (Schema Migrations)

Este diretório contém o histórico sequencial e incremental de mudanças no schema do banco de dados PostgreSQL do Core Banking MEI (`bootcamp-qitech-api`).

---

## 1. Convenção de Nomenclatura e Versionamento

Os arquivos seguem o padrão numérico sequencial com descrição do domínio:
```
database/migrations/
├── 0001_initial_core_identity.sql
├── 0002_ledger_double_entry_and_kyc.sql
├── 0003_pockets_and_governance.sql
├── 0004_charges_and_credit_ccb.sql
├── 0005_treasury_cdb_yield.sql
└── ...
```

* **Idempotência**: Todas as migrações devem utilizar `IF NOT EXISTS` para tabelas e índices, e `ON CONFLICT (enumerator) DO NOTHING` para tabelas de domínio.
* **Integridade Contábil**: Nenhuma migração destrutiva (`DROP TABLE`, `DROP COLUMN`) é permitida sem plano prévio de contingência e backward compatibility.
* **Consolidação**: O arquivo mestre [`database/database.sql`](../database.sql) reflete o estado consolidado atual de todas as migrações para inicialização limpa de contêineres Docker (`/docker-entrypoint-initdb.d/01.sql`).

---

## 2. Linha do Tempo das Mudanças

| Versão | Descrição do Schema | RFC / ADR Relacionada |
|---|---|---|
| `0001` | **Identidade & Contas**: `customer`, `account` (PF e PJ gêmeas), máquinas de estado e eventos de auditoria. | RFC 01, ADR-0005, ADR-0007 |
| `0002` | **Ledger & KYC**: `transaction`, `ledger_entry` (partidas dobradas), `idempotency_record` e `kyc_analysis`. | RFC 01, RFC 02, ADR-0004, ADR-0006 |
| `0003` | **Governança & Caixinhas**: `pocket` (DAS, emergência, trava), `transfer_policy` e `revenue_tracker` (teto R$ 81k). | RFC 03, RFC 04 |
| `0004` | **Cobrança & Crédito CCB**: `charge` (Pix, boleto, cartão), `webhook_event`, `credit_contract`, parcelas e antecipação de recebíveis. | RFC 02, RFC 04, ADR-0008 |
| `0005` | **Tesouraria & CDB**: `yield_position`, `yield_accrual_event` para remuneração diária CDI e Cash Sweep. | RFC 03 |
