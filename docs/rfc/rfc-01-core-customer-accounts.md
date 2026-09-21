# RFC 01 — Core Identity: Clientes (Customers) e Contas Vinculadas (PF e PJ)

| | |
|---|---|
| **Status** | **Aprovada (Pronta para Especificação)** |
| **Time** | João Pedro Calsavara |
| **Data** | 19/09/2026 |
| **Versão** | 3 (Incorporando decisões de Grilling, Resoluções BACEN e LC 123/2006) |

---

## Contextualização

### Entendendo o problema

O Microempreendedor Individual (MEI) é juridicamente um *Empresário Individual (213-5)*: perante o direito civil, a pessoa física (CPF) e a pessoa jurídica (CNPJ) são a mesma pessoa natural, mas perante as obrigações fiscais e o Banco Central, a operação financeira da empresa não pode se misturar com a vida pessoal.

Além da separação patrimonial, a operação bancária do MEI precisa obedecer às normas estritas do Banco Central:
1. **Segurança de Transações e Prevenção a Furto de Sessão**: A autenticação no app (login) deve ser segregada da autorização financeira, exigindo um **PIN Transacional (4 dígitos numéricos)** para qualquer movimentação.
2. **Resolução BCB nº 103/2021 (MED e Bloqueio Cautelar)**: O banco deve suportar a segregação entre saldo total e **saldo bloqueado cautelarmente (`blocked_balance_cents`)** para prevenção a fraudes.
3. **Resolução BCB nº 518/2025 (Encerramento Compulsório por "Contas-Bolsão")**: Obrigatoriedade de encerramento unilateral por irregularidades graves ou triangulação ilícita de recursos.
4. **Encerramento de Contas e Saldo Residual**: Não é permitido fechar contas com saldo positivo (`balance_cents > 0`) em encerramentos voluntários.
5. **Injeção de Liquidez (Cash-in)**: Abertura de contas nasce com saldo zero; é necessário um mecanismo de aporte de fundos com contrapartida em conta contábil interna (`SYSTEM_SETTLEMENT`).

### Explicando a solução de forma macro

A solução estabelece o conceito central de **Customer (Cliente MEI)** com **Onboarding Atômico**:
1. O empreendedor realiza uma única chamada em `POST /customers` fornecendo seus dados civis (CPF, nome, data de nascimento), seus dados empresariais (CNPJ, razão social), senha de acesso (`password`) e **PIN Transacional de 4 dígitos** (`transaction_pin`).
2. Em uma única transação atômica no PostgreSQL, o sistema:
   - Cria o registro de `Customer` com os hashes seguros de senha (`password_hash`) e de PIN (`pin_hash`) usando `Argon2id`.
   - Provisiona automaticamente **duas contas correntes interligadas**:
     - **Conta PJ (`BUSINESS`)**: vinculada ao CNPJ, destinada a operações do negócio, vendas, fornecedores e tributos.
     - **Conta PF (`PERSONAL`)**: vinculada ao CPF, destinada a despesas pessoais e recebimento de pró-labore/lucro distribuído.
3. Ambas as contas nascem com saldo zero (`balance_cents = 0`, `blocked_balance_cents = 0`) e status `active`.
4. Rota explícita de **Cash-in** (`POST /accounts/{account_key}/deposits`) credita a conta com contrapartida de débito na conta interna `SYSTEM_SETTLEMENT`, mantendo a soma algébrica do ledger igual a zero.
5. Regras de máquina de estados de conta:
   - `closed`: Exige saldo rigorosamente zero (`balance_cents == 0`). Se `balance_cents > 0`, rejeita com `409 Conflict` (`QIT001011`). Exceção para encerramento compulsório de compliance (`reason_code = COMPLIANCE_FRAUD` ou `IRREGULARITY_BCB518`).
   - `blocked`: Bloqueio unidirecional independente: saídas (`DEBIT`) são bloqueadas, mas entradas (`CREDIT`) permanecem permitidas. O bloqueio da Conta PJ não afeta a Conta PF automaticamente.

### Alternativas Descartadas e Trade-offs

- *Conta única com divisão interna apenas em "fundos/cofrinhos"* — descartada pelos riscos fiscais: a Receita Federal (e-Financeira) reporta créditos em contas CNPJ como faturamento da empresa, arriscando desenquadramento do teto de R$ 81k.
- *Permitir encerramento com saldo positivo varrendo automaticamente para a PF* — descartada porque transferências automáticas sem consentimento expresso geram confusão patrimonial involuntária e litígios.
- *Bloqueio total de crédito em contas com status `blocked`* — descartada conforme práticas do SISBAJUD: contas bloqueadas judicialmente devem aceitar créditos para quitação de execuções, mas travar débitos.
- *Testes unitários com mocks* — **descartada conforme [ADR-0001](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0001-apenas-testes-de-integracao.md)**: validações de onboarding, bloqueio cautelar e encerramento de contas são testadas exclusivamente através de **testes de integração ponta a ponta** com banco de dados real.

---

## Implementação

### Diretriz Obrigatória de Testes
> [!IMPORTANT]
> **Padrão do Projeto: Apenas Testes de Integração (Sem Testes Unitários)**
> Conforme o [ADR-0001](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0001-apenas-testes-de-integracao.md), todo teste deve residir em `tests/integration/`, exercitando os endpoints FastAPI via `TestClient` e verificando o estado persistido no PostgreSQL.

---

### Rotas

| Método | Caminho | O que faz | Entrada (campos que importam) | Saídas (status e quando) |
|---|---|---|---|---|
| `POST` | `/customers` | Submete cadastro unificado do MEI e inicia esteira de KYC/Antifraude (RFC 03) | `name`, `email`, `password`, `transaction_pin`, `cpf`, `cnpj`, `birthdate`, `legal_name` | `202` aceito com `customer_key` e status `created`; contas provisionadas automaticamente ao atingir status `active`; `400` payload inválido ou PIN não numérico (`QIT000001`); `409` duplicidade (`QIT001004`/`05`/`06`); `422` documento inválido (`QIT001003`) |
| `POST` | `/customers/login` | Autentica o cliente e emite o token JWT de acesso | `email`, `password` | `200` autenticado com `access_token` e resumo das contas do cliente; `401` credenciais inválidas (`QIT000401`) |
| `GET` | `/customers/{customer_key}` | Consulta os dados cadastrais do cliente MEI | `customer_key` no caminho | `200` dados do cliente (CPF, CNPJ, nome, e-mail); `404` cliente não encontrado (`QIT001001`) |
| `GET` | `/customers/{customer_key}/accounts` | Lista as contas vinculadas ao cliente com saldos total, bloqueado e disponível | `customer_key` no caminho | `200` lista contendo a Conta PJ (`BUSINESS`) e a Conta PF (`PERSONAL`); `404` cliente não encontrado |
| `GET` | `/accounts/{account_key}` | Consulta detalhes e saldos de uma conta específica | `account_key` no caminho | `200` detalhes da conta, tipo, status, `balance_cents`, `blocked_balance_cents` e `available_balance_cents`; `404` conta não encontrada |
| `POST` | `/accounts/{account_key}/deposits` | Executa Cash-in (depósito/aporte de liquidez) com contrapartida em conta do sistema | `amount_cents`, `description`, cabeçalho `Idempotency-Key` | `201` liquidado com `deposit_key`; `400` valor <= 0; `404` conta não encontrada; `409` conta inativa ou fechada |
| `PUT` | `/accounts/{account_key}/status` | Altera o estado da conta (ativar, bloquear, encerrar) com código de motivo formal | `status` (`active`, `blocked`, `closed`), `reason_code` (`VOLUNTARY`, `COMPLIANCE_FRAUD`, `IRREGULARITY_BCB518`, `JUDICIAL_BLOCK`), `reason` | `202` transição aceita com `account_key`; `400` status desconhecido; `404` conta não encontrada; `409` saldo > 0 em encerramento voluntário (`QIT001011`) ou transição a partir de status final (`QIT001002`) |
| `PUT` | `/accounts/{account_key}/blocked-balance` | Aplica ou remove bloqueio cautelar de saldo (Resolução BCB nº 103/2021) | `amount_cents`, `operation` (`BLOCK` ou `UNBLOCK`), `reason` | `200` saldo bloqueado atualizado; `400` valor inválido; `422` saldo disponível insuficiente para bloqueio |

---

### Banco de Dados (Diagrama ER)

```mermaid
erDiagram
    CUSTOMER ||--|{ ACCOUNT : "possui contas vinculadas (PJ e PF)"
    ACCOUNT_STATUS ||--o{ ACCOUNT : "define estado"
    ACCOUNT ||--o{ ACCOUNT_STATUS_EVENT : "gera historico"
    ACCOUNT_STATUS ||--o{ ACCOUNT_STATUS_EVENT : "registra de/para"

    CUSTOMER {
        int id PK "interno"
        char customer_key UK "UUIDv4 publico"
        int status_id FK "referencia customer_status(id) conforme RFC 03 e ADR-0007"
        string cpf UK "CPF unico do empreendedor"
        string cnpj UK "CNPJ unico do MEI"
        string name "Nome civil completo"
        string legal_name "Razao social empresarial"
        string email UK "E-mail unico para login"
        string password_hash "Hash Argon2id da senha"
        string pin_hash "Hash Argon2id do PIN de 4 digitos"
        date birthdate "Data de nascimento"
        datetime created_at
        datetime updated_at
    }

    ACCOUNT_STATUS {
        int id PK "interno"
        string enumerator UK "created, active, blocked, closed"
        datetime created_at
    }

    ACCOUNT {
        int id PK "interno"
        char account_key UK "UUIDv4 publico"
        int customer_id FK "vinculo com o Customer"
        int status_id FK "estado atual"
        string account_type "BUSINESS ou PERSONAL"
        string document_number "CNPJ para BUSINESS, CPF para PERSONAL"
        bigint balance_cents "saldo total em centavos (CHECK >= 0)"
        bigint blocked_balance_cents "saldo bloqueado cautelar MED (CHECK >= 0)"
        datetime created_at
        datetime updated_at
    }

    ACCOUNT_STATUS_EVENT {
        int id PK "interno"
        int account_id FK "qual conta"
        int from_status_id FK "estado anterior (nulo no nascimento)"
        int to_status_id FK "novo estado"
        string reason_code "VOLUNTARY, COMPLIANCE_FRAUD, IRREGULARITY_BCB518, JUDICIAL_BLOCK"
        string reason "detalhes textuais da justificativa"
        datetime event_datetime "quando ocorreu"
        datetime created_at "append-only"
    }
```

---

### Desenho de Fluxo da Rota (As Seis Perguntas Respondidas no Desenho)

#### POST /customers — Onboarding do Cliente MEI e Abertura de Contas

```mermaid
flowchart TD
    START((Início)) --> VALIDATE_INPUT["Validar payload, CPF, CNPJ e formato do PIN (4 dígitos)"]
    VALIDATE_INPUT --> CHECK_DOCS{"Documentos e PIN válidos?"}
    
    CHECK_DOCS -- "Não (400/422)" --> ERR_422["Error (400/422 QIT001003)"]
    CHECK_DOCS -- "Sim" --> CHECK_DUP["Buscar duplicidade por e-mail, CPF ou CNPJ"]
    
    CHECK_DUP --> IS_DUP{"Cliente já existe?"}
    IS_DUP -- "Sim (409)" --> ERR_409["Error (409 QIT001004/5/6)"]
    IS_DUP -- "Não" --> HASH_CREDS["Gerar hash da senha e do PIN com Argon2id"]
    
    HASH_CREDS --> ATOMIC_TX["Transação Atômica:<br/>1. Criar Customer com password_hash e pin_hash<br/>2. Criar Conta PJ (active, balance: 0, blocked: 0)<br/>3. Criar Conta PF (active, balance: 0, blocked: 0)<br/>4. Registrar eventos em account_status_event"]
    
    ATOMIC_TX --> CREATE_DTO["Criar DTO com customer_key e mapa de contas"]
    CREATE_DTO -- "201" --> SUCCESS((Success 201))

    style ERR_422 fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_409 fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style SUCCESS fill:#c8e6c9,color:#1b5e20,stroke:#1b5e20
    style START fill:#e0f2f1,color:#004d40,stroke:#004d40
    style ATOMIC_TX fill:#e1f5fe,color:#01579b,stroke:#0288d1
```

#### PUT /accounts/{account_key}/status — Encerramento e Validação de Saldo Residual

```mermaid
flowchart TD
    START((Início)) --> FIND_ACC["Buscar conta pela account_key com lock (SELECT FOR UPDATE)"]
    FIND_ACC --> ACC_EXISTS{"Conta existe?"}
    
    ACC_EXISTS -- "Não (404)" --> ERR_404["Error (404 QIT001001)"]
    ACC_EXISTS -- "Sim" --> CHECK_CLOSED{"Conta já está 'closed'?"}
    
    CHECK_CLOSED -- "Sim (409)" --> ERR_FINAL["Error (409 QIT001002 - Estado Final)"]
    CHECK_CLOSED -- "Não" --> IS_CLOSING{"Novo status é 'closed'?"}
    
    IS_CLOSING -- "Não" --> APPLY_TRANSITION["Validar transição (ex: active <-> blocked)<br/>Atualizar status_id e gravar evento"]
    IS_CLOSING -- "Sim" --> CHECK_REASON{"Motivo é COMPLIANCE_FRAUD?"}
    
    CHECK_REASON -- "Sim" --> CLOSE_FORCE["Encerramento compulsório (Res. BCB 518)<br/>Congelar saldo e fechar conta"]
    CHECK_REASON -- "Não" --> CHECK_BALANCE{"Saldo é rigorosamente zero?<br/>balance_cents == 0"}
    
    CHECK_BALANCE -- "Não (409)" --> ERR_BALANCE["Error (409 QIT001011 - Saldo Residual > 0)"]
    CHECK_BALANCE -- "Sim" --> CLOSE_OK["Atualizar status para 'closed'<br/>Gravar evento com reason_code"]
    
    APPLY_TRANSITION --> DTO_ACCEPTED["Criar DTO"]
    CLOSE_FORCE --> DTO_ACCEPTED
    CLOSE_OK --> DTO_ACCEPTED
    DTO_ACCEPTED -- "202" --> SUCCESS((Success 202))

    style ERR_404 fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_FINAL fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_BALANCE fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style SUCCESS fill:#c8e6c9,color:#1b5e20,stroke:#1b5e20
    style START fill:#e0f2f1,color:#004d40,stroke:#004d40
```

---

## Principal Desafio

- **Qual é:** Garantir atomicidade no onboarding conjunto, segurança contra fraudes via PIN transacional independente e conformidade regulatória estrita com as resoluções do BACEN (MED e Resolução 518/2025).
- **Como o desenho resolve:** Inserção em transação única no PostgreSQL com separação de credenciais (senha e PIN), controle nativo de saldo cautelar (`blocked_balance_cents`) e auditoria imutável de transições de conta com códigos de motivo formal.
