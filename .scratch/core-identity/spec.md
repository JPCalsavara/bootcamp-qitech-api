# Spec: Core Identity — Clientes (Customers), Contas Vinculadas (PF e PJ) e Ciclo de Vida

## Problem Statement

O Microempreendedor Individual (MEI) enfrenta uma barreira estrutural nos bancos tradicionais: a separação burocrática entre sua pessoa física e sua pessoa jurídica. Para conseguir operar seu negócio, ele é obrigado a passar por múltiplos cadastros demorados e fragmentados (abrir primeiro uma conta PF, depois cadastrar a empresa, depois solicitar uma conta PJ). Essa fricção incentiva o MEI a misturar finanças pessoais e empresariais em uma única conta, gerando desorganização de caixa e sérios passivos tributários perante a Receita Federal.

Além disso, do ponto de vista de segurança e compliance bancário (Resoluções BCB nº 103/2021 e 518/2025):
- Uma sessão de login comprometida no app pode expor os fundos do empreendedor se não houver um segundo fator de autorização para movimentações financeiras.
- Contas de pagamento precisam suportar bloqueios cautelares temporários contra fraudes (MED).
- Contas não podem ser encerradas voluntariamente contendo saldo residual positivo, evitando perdas de fundos e disputas judiciais.

## Solution

Criar o subsistema de **Core Identity** do CoreBank MEI com **Onboarding Unificado e Atômico**:
1. Através de um único endpoint (`POST /customers`), o empreendedor informa seus dados civis (CPF, nome, data de nascimento), empresariais (CNPJ, razão social), senha de acesso e um **PIN Transacional numérico de 4 dígitos**.
2. Em uma única transação atômica no banco de dados local, o sistema cria o cadastro do `Customer` (com hashes seguros Argon2id de senha e PIN) e já provisiona **duas contas correntes ativas e interligadas**:
   - **Conta PJ (`BUSINESS`)**: vinculada ao CNPJ para recebimento de vendas, fornecedores e tributos.
   - **Conta PF (`PERSONAL`)**: vinculada ao CPF para despesas pessoais e retiradas de pró-labore/lucro.
3. Disponibilizar endpoints para autenticação JWT (`POST /customers/login`), consulta cadastral e listagem das contas vinculadas.
4. Suportar injeção de liquidez via **Cash-in** (`POST /accounts/{account_key}/deposits`) contra uma conta interna do banco (`SYSTEM_SETTLEMENT`).
5. Implementar a máquina de estados de contas com tabela de histórico append-only (`account_status_event`), bloqueio cautelar de saldo (`blocked_balance_cents`) e trava de encerramento para contas com saldo positivo (`balance_cents > 0`).

## User Stories

1. As a MEI entrepreneur, I want to sign up with my CPF and CNPJ in a single step, so that I don't have to fill out multiple fragmented registration forms.
2. As a MEI entrepreneur, I want my Business (PJ) and Personal (PF) accounts to be created simultaneously upon registration, so that I can immediately start segregating my company's finances from my personal spending.
3. As a MEI entrepreneur, I want to define a 4-digit numeric transaction PIN during onboarding, so that my money is protected even if someone gains access to my login session.
4. As a MEI entrepreneur, I want to log in using my email and password to receive an access token, so that I can securely interact with the bank's API.
5. As a MEI entrepreneur, I want to view my customer details (name, email, CPF, CNPJ), so that I can verify that my registered profile is correct.
6. As a MEI entrepreneur, I want to list all accounts linked to my profile with their current balances, so that I have a clear view of both my business capital and my personal funds.
7. As a MEI entrepreneur, I want to deposit funds (cash-in) into my account, so that I can add initial liquidity to start making payments and transfers.
8. As a compliance officer, I want each cash-in deposit to be balanced against an internal bank settlement account, so that the bank's double-entry accounting maintains an algebraic sum of zero.
9. As a compliance officer, I want the system to reject registrations with invalid CPFs or CNPJs with a 422 error, so that invalid tax documents do not enter the core banking ledger.
10. As a compliance officer, I want the system to reject duplicate emails, CPFs, or CNPJs with a 409 error, so that identity uniqueness is preserved.
11. As a risk analyst, I want to apply a temporary precautionary block on an account's balance (blocked_balance_cents), so that suspicious funds under fraud investigation (MED) cannot be withdrawn.
12. As a risk analyst, I want to remove a precautionary block once an investigation is cleared, so that the customer regains access to their available balance.
13. As an account manager, I want to block an account unilaterally for outgoing transfers while still allowing incoming credits, so that legal requirements (SISBAJUD) are met without rejecting debt payments.
14. As an account manager, I want an account block on the Business account to remain independent from the Personal account, so that personal survival funds are not automatically frozen due to a corporate dispute.
15. As a MEI entrepreneur, I want to voluntarily close my account when I no longer need it, provided its balance is strictly zero.
16. As a system operator, I want to reject voluntary account closures if the account has a positive balance with a 409 error, so that the customer is forced to withdraw their money first.
17. As a compliance officer, I want to force the closure of an account involved in severe fraud or third-party triangulation (Resolução BCB nº 518/2025), regardless of remaining balance, with an audited reason code.
18. As an auditor, I want every account status transition to be recorded in an immutable append-only event table, so that we have a complete forensic trail of who changed what and why.

## Implementation Decisions

- **Customer Entity**:
  - Central table `customer` containing `customer_key` (UUIDv4), `cpf` (11 chars), `cnpj` (14 chars), `name`, `legal_name`, `email`, `password_hash`, `pin_hash`, `is_active`, `birthdate`, `created_at`, `updated_at`.
  - Passwords and PINs hashed with `Argon2id` (or Bcrypt) with cryptographic salt.
  - Unique constraints on `email`, `cpf`, and `cnpj`.
- **Account Entity & Status Lifecycle**:
  - Table `account` containing `account_key` (UUIDv4), `customer_id` (FK to `customer`), `status_id` (FK to `account_status`), `account_type` (`BUSINESS` or `PERSONAL`), `document_number`, `balance_cents` (BIGINT, CHECK >= 0), `blocked_balance_cents` (BIGINT, CHECK >= 0).
  - Virtual/computed property: `available_balance_cents = balance_cents - blocked_balance_cents`.
  - Lookup table `account_status` (`created`, `active`, `blocked`, `closed`).
  - Table `account_status_event` (append-only) tracking `account_id`, `from_status_id`, `to_status_id`, `reason_code` (`VOLUNTARY`, `COMPLIANCE_FRAUD`, `IRREGULARITY_BCB518`, `JUDICIAL_BLOCK`), `reason`, `event_datetime`.
- **API Contracts**:
  - `POST /customers`: Single-step atomic creation of Customer + Business Account + Personal Account.
  - `POST /customers/login`: Returns Bearer JWT token.
  - `GET /customers/{customer_key}`: Returns customer profile.
  - `GET /customers/{customer_key}/accounts`: Returns both accounts with balances.
  - `GET /accounts/{account_key}`: Returns account details and balances.
  - `POST /accounts/{account_key}/deposits`: Cash-in endpoint with `Idempotency-Key`.
  - `PUT /accounts/{account_key}/status`: Account lifecycle management with lock (`SELECT FOR UPDATE`).
  - `PUT /accounts/{account_key}/blocked-balance`: Precautionary lock management.
- **Architectural Seam**:
  - Follows the existing codebase structure: `resources/` (HTTP boundary with JSON schema validation), `controllers/` (orchestration, state transitions, transactions), `repositories/` (SQLAlchemy queries and pessimistic locks), `models/` (declarative SQLAlchemy models), and `dtos/` (response formatting).

## Testing Decisions

- **Testing Seam**: The highest possible seam — strictly the HTTP endpoint surface. All tests execute via HTTP requests (`ClientRequisition` / `RequestGenerator`) against the running application.
- **Local Mocked Environment**:
  - PostgreSQL test database running locally via Docker (`docker compose up`), configured via `DATABASE_URL`.
  - Database schema reset via `DbUtils.rollback()` before tests that depend on counts, listings, or clean state.
  - Any external connectors (e.g. third-party APIs) point to mock URLs.
- **Test Scenarios**:
  - Validation tests: Malformed payloads, invalid CPF check digits, invalid CNPJ check digits, non-numeric or non-4-digit PINs (`400`/`422`).
  - Conflict tests: Duplicate email, duplicate CPF, duplicate CNPJ (`409`).
  - Happy path tests: Unified registration creates Customer, Business account, Personal account, and status events (`201`).
  - Login tests: Valid credentials return JWT; invalid credentials return `401`.
  - Cash-in tests: Successful deposit increases `balance_cents` and is idempotent (`201`).
  - Account status tests:
    - Attempting to close account with `balance_cents > 0` returns `409 QIT001011`.
    - Closing account with `balance_cents == 0` succeeds (`202`).
    - Attempting transition from `closed` returns `409 QIT001002`.
    - Blocking account succeeds (`202`) and allows subsequent credits while blocking debits.
  - Precautionary block tests: Blocking and unblocking `blocked_balance_cents`.

## Out of Scope

- Self-service password recovery via email (forgot password).
- Biometric facial validation (Liveness/KYC document upload).
- Integration with live external banking networks (SPB/PIX DICT).
- Multiple users/operators per MEI (delegated accountant access).

## Further Notes

- All monetary values are strictly represented in integer cents (`BIGINT`).
- The spec aligns with [ADR-0001](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0001-apenas-testes-de-integracao.md), [RFC 01](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/rfc/rfc-01-core-customer-accounts.md), and [CONTEXT.md](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/CONTEXT.md).

