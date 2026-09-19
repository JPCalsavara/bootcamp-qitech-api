# Spec: Core Transactions — Motor Financeiro, Ledger de Partidas Dobradas e Idempotência

## Problem Statement

A operação de transferências financeiras em um sistema bancário é o ponto de maior criticidade e risco de falhas catastróficas. Os três problemas fundamentais são:
1. **Divergência Contábil e Falta de Rastreabilidade**: Se o saldo de uma conta for apenas uma coluna modificada diretamente (`UPDATE account SET balance = ...`), não há prova forense de onde o dinheiro veio ou para onde foi. É indispensável um livro-razão (*ledger*) de partidas dobradas (*double-entry*) imutável, onde todo débito possua um crédito simétrico correspondente.
2. **Deadlocks sob Concorrência Bilateral**: Quando duas contas transferem valores uma para a outra simultaneamente no mesmo milissegundo, ocorrem bloqueios cruzados de linha no banco de dados. Sem ordenação determinística de travas, o PostgreSQL detecta espera circular e aborta transações (`40P01`), gerando erros 500 para os clientes.
3. **Cobrança Duplicada por Falha de Rede**: Retentativas de clientes após timeouts podem processar transferências repetidas se não houver um controle de idempotência persistente que reconheça tanto sucessos quanto falhas de validação.
4. **Segurança e Conformidade Tributária (Art. 14 da LC 123/2006)**: Transferências financeiras precisam de autorização de segundo fator via PIN transacional numérico, e transferências da Conta PJ para a Conta PF do mesmo MEI devem ser etiquetadas como Distribuição de Lucros Isenta para garantir 100% de isenção de IRPF perante a Receita Federal.

## Solution

Criar o subsistema de **Core Transactions** do CoreBank MEI:
1. **Execução de Transferências (`POST /transactions`)**:
   - Valida o `Idempotency-Key` contra a tabela dedicada `idempotency_record` com TTL de 24 horas.
   - Valida o `transaction_pin` contra o `pin_hash` do `Customer`.
   - Adquire locks pessimistas de linha via `SELECT FOR UPDATE` utilizando a **Hierarquia Global de Dijkstra** (`sorted([origin_id, destination_id])`), prevenindo matematicamente deadlocks.
   - Valida o saldo disponível da conta de origem (`balance_cents - blocked_balance_cents >= amount_cents`).
   - Classifica automaticamente transferências da Conta PJ para a Conta PF do mesmo titular como `transaction_type = "PROFIT_DISTRIBUTION"`.
   - Insere atomicamente a `transaction` com `end_to_end_id` padronizado e dois registros imutáveis em `ledger_entry` (`DEBIT` na origem e `CREDIT` no destino, ambos gravando `balance_after_cents`).
   - Atualiza os saldos de leitura rápida em `account`.
   - Salva a resposta em `idempotency_record` e retorna `201 Created`.
2. **Mecânica de Estorno (`POST /transactions/{transaction_key}/reversals`)**:
   - Cria nova transação de estorno com lançamentos contábeis invertidos (`CREDIT` na origem original e `DEBIT` no destino original).
   - Valida se a conta recebedora original possui saldo disponível suficiente; se não possuir, rejeita com `422 Unprocessable Entity` (`QIT001012`), impedindo saldo negativo desautorizado.
3. **Extrato Contábil Enriquecido (`GET /accounts/{account_key}/statement`)**:
   - Emite o histórico paginado de lançamentos contendo contraparte (nome e documento), tipo fiscal da operação (`PROFIT_DISTRIBUTION`, `TRANSFER`, `DEPOSIT`, `REVERSAL`), valor e saldo resultante da época (`balance_after_cents`).

## User Stories

1. As a MEI entrepreneur, I want to transfer money from my Business account to my Personal account, so that I can pay myself a profit distribution for my personal living expenses.
2. As a MEI entrepreneur, I want my internal Business-to-Personal transfers to be formally classified as Profit Distribution (Art. 14 LC 123/2006), so that I have complete accounting proof for 100% tax-free income on my annual income tax return.
3. As a MEI entrepreneur, I want to transfer money to another account using their account key, so that I can pay suppliers and partners.
4. As a MEI entrepreneur, I want the system to require my 4-digit transaction PIN for every transfer, so that unauthorized transfers cannot be made even if someone has my access token.
5. As an API client, I want to send an Idempotency-Key header with every transfer request, so that network timeouts and retries do not result in duplicate debits.
6. As an API client, I want a retried request with the same Idempotency-Key and payload to return the original cached response immediately, so that my client application can safely recover from lost network connections.
7. As an API client, I want a retried request with the same Idempotency-Key but a different payload to be rejected with a 409 Conflict error, so that payload tampering or key reuse is detected.
8. As a compliance officer, I want each transfer to generate a unique End-to-End ID (BACEN standard), so that every movement is universally traceable across financial systems.
9. As a financial auditor, I want every transfer to create two balanced ledger entries (DEBIT and CREDIT) with identical amounts, so that the bank's ledger obeys double-entry bookkeeping.
10. As a financial auditor, I want ledger entries to be strictly immutable and append-only, so that financial history can never be altered or deleted.
11. As a MEI entrepreneur, I want to view my account statement with pagination and date filters, so that I can review my financial history and share it with my accountant.
12. As a MEI entrepreneur, I want my statement to display the counterparty name, document, operation type, and the balance immediately after each entry, so that I can easily reconcile my cash flow.
13. As a system operator, I want concurrent transfers between the same two accounts in opposite directions to execute without database deadlocks (error 40P01), so that the system remains stable under heavy traffic.
14. As an account manager, I want to reverse a settled transaction, so that operational errors or fraudulent charges can be rectified.
15. As an account manager, I want an attempted reversal to be rejected with a 422 error if the receiving account no longer has sufficient available balance, so that accounts are never forced into an unauthorized negative balance.
16. As a risk analyst, I want transfers from an account with status 'blocked' to be rejected with a 409 error, so that frozen accounts cannot move money out.
17. As a risk analyst, I want transfers to an account with status 'blocked' to be accepted and credited, so that debts can still be received into blocked accounts (SISBAJUD compliance).
18. As a customer, I want transfers that exceed my available balance (balance_cents - blocked_balance_cents) to be rejected with a 422 error, so that I cannot spend money that is reserved or blocked.

## Implementation Decisions

- **Transaction & Ledger Entities**:
  - Table `transaction` containing `id` (PK), `transaction_key` (UUIDv4), `end_to_end_id` (UK, BACEN standard: `E` + ISPB + timestamp + random), `origin_account_id` (FK), `destination_account_id` (FK), `status_id` (FK to `transaction_status`), `transaction_type` (`TRANSFER`, `PROFIT_DISTRIBUTION`, `DEPOSIT`, `REVERSAL`), `amount_cents` (BIGINT, CHECK > 0), `description`, `reversal_of_transaction_id` (FK nullable), `created_at`.
  - Lookup table `transaction_status` (`pending`, `settled`, `failed`, `reversed`).
  - Table `transaction_status_event` (append-only) tracking status transitions.
  - Table `ledger_entry` (append-only) containing `id` (PK), `account_id` (FK), `transaction_id` (FK), `entry_type` (`DEBIT` or `CREDIT`), `amount_cents` (BIGINT, CHECK > 0), `balance_after_cents` (BIGINT, CHECK >= 0), `created_at`.
- **Idempotency Record Entity**:
  - Dedicated table `idempotency_record` containing `id` (PK), `idempotency_key` (VARCHAR(128), UK), `request_path`, `request_hash` (SHA-256), `response_code` (INT), `response_body` (TEXT), `expires_at` (DATETIME, 24h TTL), `created_at`.
  - Stored within the transaction or committed before long processing to handle concurrent duplicate calls.
- **Deadlock Prevention (Dijkstra's Hierarchy)**:
  - Account locks are always acquired using deterministically sorted IDs: `sorted([origin_account_id, destination_account_id])`.
  - SQL: `SELECT ... FROM account WHERE id IN (:id1, :id2) ORDER BY id FOR UPDATE`.
- **API Contracts**:
  - `POST /transactions`: Bilateral transfer execution with `Idempotency-Key` and `transaction_pin`.
  - `POST /transactions/{transaction_key}/reversals`: Transaction reversal with balance check.
  - `GET /transactions/{transaction_key}`: Detailed transaction query.
  - `GET /accounts/{account_key}/statement`: Enriched paginated statement query.
- **Architectural Seam**:
  - `resources/` (validates JSON schema and headers), `controllers/` (orchestrates Dijkstra ordering, PIN verification, double-entry insertion, and session commit), `repositories/` (SQLAlchemy queries and ordered pessimistic locks), and `dtos/` (statement and transaction outputs).

## Testing Decisions

- **Testing Seam**: Strictly the HTTP endpoint boundary (`POST /transactions`, `POST /transactions/{key}/reversals`, `GET /accounts/{key}/statement`) via `ClientRequisition` / `RequestGenerator`.
- **Local Mocked Environment**:
  - Tests run against the local PostgreSQL test database configured in `DATABASE_URL`.
  - `DbUtils.rollback()` used to reset the database when running statement listing or count tests.
- **Test Scenarios**:
  - Validation tests: Missing PIN, incorrect PIN (`401`), non-existent account keys (`404`), negative or zero amount (`400`).
  - Balance tests: Transfer amount exceeding available balance (`balance_cents - blocked_balance_cents`) returns `422 QIT001010`.
  - Happy path tests: Valid transfer debits origin, credits destination, inserts two ledger entries, creates settled transaction and returns `201`.
  - Profit distribution tests: Transfer from Business to Personal account of same Customer is verified to have `transaction_type == 'PROFIT_DISTRIBUTION'`.
  - Idempotency tests:
    - Sending same key + same payload returns original response with same `transaction_key` (`201`).
    - Sending same key + different payload returns `409 QIT001008`.
  - Concurrency & Deadlock tests:
    - Two concurrent HTTP requests transferring between Account A and Account B in opposite directions simultaneously.
    - Assert that both succeed or complete cleanly without PostgreSQL deadlock error (`40P01`).
  - Reversal tests:
    - Reversing settled transaction creates reversal transaction and inverse ledger entries (`201`).
    - Attempting reversal when destination has spent funds returns `422 QIT001012`.
    - Attempting to reverse an already reversed transaction returns `409`.
  - Statement tests:
    - Verified that each entry includes `counterparty_name`, `counterparty_document`, `transaction_type`, and `balance_after_cents`.

## Out of Scope

- Scheduled future transfers (agendamento).
- Recurring transfers (pagamentos recorrentes/assinaturas).
- Multi-party payment splits (divisão de pagamentos entre 3 ou mais contas).
- Direct integration with Banco Central PIX SPI/DICT networks.

## Further Notes

- All monetary values are strictly represented in integer cents (`BIGINT`).
- The spec aligns with [ADR-0001](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0001-apenas-testes-de-integracao.md), [RFC 02](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/rfc-02-transactions-ledger.md), and [CONTEXT.md](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/CONTEXT.md).
