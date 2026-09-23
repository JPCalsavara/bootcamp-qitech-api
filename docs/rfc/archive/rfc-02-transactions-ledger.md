# RFC 02 — Core Transactions: Motor Financeiro, Ledger de Partidas Dobradas e Idempotência

| | |
|---|---|
| **Status** | **Aprovada (Pronta para Especificação)** |
| **Time** | João Pedro Calsavara |
| **Data** | 19/09/2026 |
| **Versão** | 3 (Incorporando decisões de Grilling, Idempotência com TTL, Estornos e LC 123/2006) |

---

## Contextualização

### Entendendo o problema

No núcleo de um sistema bancário, as transferências financeiras precisam cumprir requisitos inegociáveis de engenharia financeira, segurança e conformidade regulatória:
1. **Precisão Contábil e Auditoria Forense**: O saldo nunca é uma coluna mutável sem lastro. Toda movimentação deve ser lastreada por um livro-razão (*ledger*) de partidas dobradas (*double-entry*), onde a soma algébrica de débitos e créditos de qualquer transação é rigorosamente zero.
2. **Prevenção de Deadlocks sob Alta Concorrência**: Transferências simultâneas e cruzadas entre contas no mesmo milissegundo adquirem locks de linha em ordens opostas, causando deadlocks no banco (`40P01`) e derrubando requisições se não houver ordenação determinística.
3. **Idempotência com Tabela Dedicada e TTL**: Retentativas causadas por instabilidades de rede não podem reprocessar pagamentos nem colidir. A idempotência deve ser gerenciada em tabela dedicada (`idempotency_record`) com TTL de 24 horas, gravando tanto respostas de sucesso quanto respostas de erro.
4. **Segurança de Execução (PIN Transacional)**: O token de login (JWT) não é suficiente para transferir fundos; a operação exige a verificação criptográfica do **PIN Transacional de 4 dígitos** do titular.
5. **Classificação Fiscal (Art. 14 da LC 123/2006)**: Transferências da Conta PJ para a Conta PF do mesmo titular representam **Distribuição de Lucros Isenta** e devem ser etiquetadas como tal no ledger para fins contábeis e fiscais do MEI.
6. **Mecânica Estrita de Estornos (`reversed`)**: Estornos geram lançamentos contábeis invertidos e exigem verificação de saldo disponível na conta recebedora. Se a conta de destino não tiver saldo livre suficiente, o estorno falha com erro semântico, impedindo saldo negativo desautorizado.

### Explicando a solução de forma macro

A solução combina seis pilares de engenharia financeira:
- **Ledger Imutável de Partidas Dobradas**: A tabela `ledger_entry` é exclusivamente append-only. Cada transferência insere atomicamente um registro de `DEBIT` na conta de origem e um registro de `CREDIT` na conta de destino, ambos com o mesmo valor em centavos inteiros (`BIGINT`).
- **Hierarquia Global de Locks de Dijkstra**: Antes de adquirir travas de linha via `SELECT FOR UPDATE`, o sistema ordena deterministicamente os identificadores numéricos das contas (`sorted([origin_id, destination_id])`), tornando a espera circular matematicamente impossível.
- **Tabela Dedicada de Idempotência (`idempotency_record`)**: Armazena `idempotency_key`, hash do payload, código de resposta HTTP e corpo de resposta com expiração de 24h. Requisições concorrentes ou retentadas recebem a resposta em cache ou erro de conflito (`409 QIT001008`).
- **Verificação de Saldo Disponível**: A conta de origem só pode transferir valores se `balance_cents - blocked_balance_cents >= amount_cents`.
- **Identificador Fim a Fim Padronizado (`end_to_end_id`)**: Cada transação gera um identificador único de rastreabilidade no padrão do Banco Central.
- **Extrato Contábil Enriquecido**: Cada item do extrato retorna os dados da contraparte (nome e documento), a classificação fiscal (`PROFIT_DISTRIBUTION`, `TRANSFER`, `DEPOSIT`) e o saldo resultante imediatamente após o lançamento (`balance_after_cents`).

### Alternativas Descartadas e Trade-offs

- *Idempotência apenas como coluna na tabela `transaction`* — descartada porque não permitiria cachear falhas de validação nem controlar locks de requisições em voo.
- *Permitir que estornos deixem o saldo negativo (overdraft/cheque especial forçado)* — descartada por compliance bancário e proteção contra inadimplência: o estorno só é liquidado se houver fundos suficientes.
- *Ponto flutuante (`FLOAT`/`DOUBLE`) para valores monetários* — descartada pelos erros de arredondamento inerentes ao padrão IEEE 754.
- *Testes unitários com mocks de transação* — **descartada conforme [ADR-0001](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0001-apenas-testes-de-integracao.md)**: concorrência, idempotência e integridade do ledger são testadas exclusivamente através de **testes de integração** reais no PostgreSQL.

---

## Implementação

### Diretriz Obrigatória de Testes
> [!IMPORTANT]
> **Padrão do Projeto: Apenas Testes de Integração (Sem Testes Unitários)**
> Conforme definido no [ADR-0001](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0001-apenas-testes-de-integracao.md), todo o motor financeiro deve ser coberto por testes de integração ponta a ponta (`tests/integration/`), testando concorrência real com múltiplas threads/conexões simultâneas no banco de dados.

---

### Rotas

| Método | Caminho | O que faz | Entrada (campos que importam) | Saídas (status e quando) |
|---|---|---|---|---|
| `POST` | `/transactions/transfers` | Executa transferência bilateral atômica, validando PIN e idempotência | `origin_account_key`, `destination_account_key`, `amount_cents`, `description`, `transaction_pin`, cabeçalho `Idempotency-Key` | `201` liquidada com `transaction_key` e `end_to_end_id`; `400` payload inválido (`QIT000001`); `401` PIN transacional inválido (`QIT000402`); `404` conta de origem ou destino não encontrada (`QIT001001`); `409` conflito de idempotência (`QIT001008`) ou conta de origem bloqueada/inativa (`QIT001009`); `422` saldo disponível insuficiente (`QIT001010`) |
| `POST` | `/transactions/{transaction_key}/reversals` | Executa estorno de uma transação liquidada | `reason`, `transaction_pin`, cabeçalho `Idempotency-Key` | `201` estorno liquidado com nova transação de contrapartida; `401` PIN inválido; `404` transação original não encontrada; `409` transação já estornada; `422` conta recebedora original não possui saldo suficiente para suportar o estorno (`QIT001012`) |
| `GET` | `/transactions/{transaction_key}` | Consulta detalhes e status de uma transação específica | `transaction_key` no caminho | `200` detalhes da transação, contas envolvidas, valor, tipo fiscal e status; `404` transação não encontrada |
| `GET` | `/accounts/{account_key}/statement` | Emite o extrato de lançamentos contábeis enriquecido | `account_key` no caminho, `limit`, `page`, `start_date`, `end_date` | `200` extrato paginado contendo: contraparte (nome/documento), tipo fiscal (`PROFIT_DISTRIBUTION`, `TRANSFER`, etc.), valor, data e `balance_after_cents`; `404` conta não encontrada (`QIT001001`) |

---

### Banco de Dados (Diagrama ER)

```mermaid
erDiagram
    ACCOUNT ||--o{ TRANSACTION : "origem"
    ACCOUNT ||--o{ TRANSACTION : "destino"
    ACCOUNT ||--o{ LEDGER_ENTRY : "movimenta"

    TRANSACTION_STATUS ||--o{ TRANSACTION : "define estado"
    TRANSACTION ||--o{ TRANSACTION_STATUS_EVENT : "gera historico"
    TRANSACTION_STATUS ||--o{ TRANSACTION_STATUS_EVENT : "registra de/para"

    TRANSACTION ||--|{ LEDGER_ENTRY : "origina partidas dobradas"
    IDEMPOTENCY_RECORD ||--o| TRANSACTION : "garante unicidade"

    ACCOUNT {
        int id PK "interno"
        char account_key UK "UUIDv4 publico"
        int status_id FK "estado atual"
        bigint balance_cents "saldo total (CHECK >= 0)"
        bigint blocked_balance_cents "saldo bloqueado cautelar (CHECK >= 0)"
    }

    TRANSACTION_STATUS {
        int id PK "interno"
        string enumerator UK "pending, settled, failed, reversed"
        datetime created_at
    }

    TRANSACTION {
        int id PK "interno"
        char transaction_key UK "UUIDv4 publico"
        string end_to_end_id UK "identificador fim a fim BACEN"
        int origin_account_id FK "conta debito"
        int destination_account_id FK "conta credito"
        int status_id FK "estado atual"
        string transaction_type "TRANSFER, PROFIT_DISTRIBUTION, DEPOSIT, REVERSAL, FEE_DEBIT, CREDIT_DISBURSEMENT, CREDIT_AMORTIZATION, RECEIVABLES_ANTICIPATION, TREASURY_YIELD, CHARGEBACK_DEBIT"
        bigint amount_cents "valor positivo em centavos (CHECK > 0)"
        string description "descricao da operacao"
        int reversal_of_transaction_id FK "referencia a transacao original em caso de estorno"
        datetime created_at "data da requisicao"
    }

    TRANSACTION_STATUS_EVENT {
        int id PK "interno"
        int transaction_id FK "transacao vinculada"
        int from_status_id FK "estado anterior"
        int to_status_id FK "novo estado"
        string reason "justificativa da transicao"
        datetime event_datetime "quando ocorreu"
        datetime created_at "append-only"
    }

    LEDGER_ENTRY {
        int id PK "interno"
        int account_id FK "conta afetada"
        int transaction_id FK "transacao vinculada"
        string entry_type "DEBIT ou CREDIT"
        bigint amount_cents "valor absoluto em centavos"
        bigint balance_after_cents "saldo da conta imediatamente apos este lancamento"
        datetime created_at "append-only (imutavel)"
    }

    IDEMPOTENCY_RECORD {
        int id PK "interno"
        string idempotency_key UK "chave enviada pelo cliente"
        string request_path "endpoint requisitado"
        string request_hash "hash SHA-256 do payload"
        int response_code "codigo HTTP gerado (ex: 201, 422)"
        string response_body "payload de resposta salvo"
        datetime expires_at "expiracao apos 24 horas"
        datetime created_at
    }
```

---

### Desenho de Fluxo da Rota (As Seis Perguntas Respondidas no Desenho)

#### POST /transactions — Execução de Transferência, Validação de PIN e Partidas Dobradas

```mermaid
flowchart TD
    START((Início)) --> CHECK_IDEM["Verificar tabela idempotency_record"]
    CHECK_IDEM --> HAS_IDEM{"Chave já registrada?"}
    
    HAS_IDEM -- "Sim" --> CHECK_HASH{"Mesmo request_hash?"}
    CHECK_HASH -- "Sim" --> RETURN_CACHE["Retornar resposta em cache do idempotency_record"]
    RETURN_CACHE --> END_CACHE((Success/Error Cache))
    CHECK_HASH -- "Não" --> ERR_409_IDEM["Error (409 QIT001008 - Conflito de Idempotência)"]
    
    HAS_IDEM -- "Não" --> VALIDATE_PIN["Validar transaction_pin contra pin_hash do Customer"]
    VALIDATE_PIN --> PIN_OK{"PIN correto?"}
    
    PIN_OK -- "Não (401)" --> ERR_401["Error (401 QIT000402 - PIN Inválido)"]
    PIN_OK -- "Sim" --> FIND_ACCOUNTS["Buscar contas pelas keys com ordenação de Dijkstra: sorted(origin_id, dest_id) e SELECT FOR UPDATE"]
    
    FIND_ACCOUNTS --> ACCOUNTS_EXIST{"Ambas as contas existem?"}
    ACCOUNTS_EXIST -- "Não (404)" --> ERR_404["Error (404 QIT001001)"]
    ACCOUNTS_EXIST -- "Sim" --> CHECK_ACTIVE{"Origem ativa? Destino ativo ou blocked (aceita crédito)?"}
    
    CHECK_ACTIVE -- "Não (409)" --> ERR_409_INACTIVE["Error (409 QIT001009 - Conta Inativa)"]
    CHECK_ACTIVE -- "Sim" --> CHECK_BALANCE{"Origem tem saldo livre suficiente?<br/>balance_cents - blocked_balance_cents >= amount_cents"}
    
    CHECK_BALANCE -- "Não (422)" --> ERR_422_FUNDS["Error (422 QIT001010 - Saldo Disponível Insuficiente)"]
    CHECK_BALANCE -- "Sim" --> CLASSIFY_TX{"Origem é PJ e Destino é PF do mesmo Customer?"}
    
    CLASSIFY_TX -- "Sim" --> SET_PROFIT["transaction_type = PROFIT_DISTRIBUTION (Art. 14 LC 123)"]
    CLASSIFY_TX -- "Não" --> SET_TRANSFER["transaction_type = TRANSFER"]
    
    SET_PROFIT --> ATOMIC_TRANSFER
    SET_TRANSFER --> ATOMIC_TRANSFER
    
    ATOMIC_TRANSFER["Transação Atômica:<br/>1. Inserir Transaction com end_to_end_id e status 'settled'<br/>2. Inserir LedgerEntry DEBIT na origem (com balance_after_cents)<br/>3. Inserir LedgerEntry CREDIT no destino (com balance_after_cents)<br/>4. Atualizar saldos de leitura em account<br/>5. Gravar resposta em idempotency_record (TTL 24h)"]
    
    ATOMIC_TRANSFER --> CREATE_DTO["Criar DTO enriquecido com transaction_key e end_to_end_id"]
    CREATE_DTO -- "201" --> SUCCESS((Success 201))

    style ERR_409_IDEM fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_401 fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_404 fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_409_INACTIVE fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_422_FUNDS fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style SUCCESS fill:#c8e6c9,color:#1b5e20,stroke:#1b5e20
    style END_CACHE fill:#e0f2f1,color:#004d40,stroke:#004d40
    style START fill:#e0f2f1,color:#004d40,stroke:#004d40
    style ATOMIC_TRANSFER fill:#e1f5fe,color:#01579b,stroke:#0288d1
```

#### POST /transactions/{transaction_key}/reversals — Estorno Contábil com Verificação de Saldo

```mermaid
flowchart TD
    START_REV((Início)) --> FIND_ORIGINAL["Buscar transação original pela transaction_key"]
    FIND_ORIGINAL --> TX_EXISTS{"Transação existe e status == 'settled'?"}
    
    TX_EXISTS -- "Não (404/409)" --> ERR_TX_STATUS["Error (404/409 - Transação Inexistente ou Não Liquidada)"]
    TX_EXISTS -- "Sim" --> LOCK_ACCOUNTS["Adquirir locks ordenados de Dijkstra nas contas participantes"]
    
    LOCK_ACCOUNTS --> CHECK_DEST_BALANCE{"Conta recebedora original possui saldo disponível suficiente?<br/>available_balance_cents >= original_amount"}
    
    CHECK_DEST_BALANCE -- "Não (422)" --> ERR_REV_FUNDS["Error (422 QIT001012 - Saldo Insuficiente para Estorno)"]
    CHECK_DEST_BALANCE -- "Sim" --> ATOMIC_REVERSAL["Transação Atômica:<br/>1. Criar nova Transaction (type = REVERSAL, reversal_of_transaction_id = original.id)<br/>2. Atualizar status da original para 'reversed'<br/>3. Inserir LedgerEntry DEBIT na conta recebedora original<br/>4. Inserir LedgerEntry CREDIT na conta pagadora original<br/>5. Atualizar saldos em account"]
    
    ATOMIC_REVERSAL --> DTO_REV["Criar DTO de Estorno"]
    DTO_REV -- "201" --> SUCCESS_REV((Success 201))

    style ERR_TX_STATUS fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_REV_FUNDS fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style SUCCESS_REV fill:#c8e6c9,color:#1b5e20,stroke:#1b5e20
    style START_REV fill:#e0f2f1,color:#004d40,stroke:#004d40
    style ATOMIC_REVERSAL fill:#e1f5fe,color:#01579b,stroke:#0288d1
```

---

## Principal Desafio

- **Qual é:** Concorrência extrema sem Deadlocks, gestão completa de idempotência resiliente a falhas e consistência fiscal/contábil estrita entre as contas de pessoa jurídica e física do MEI.
- **Como o desenho resolve:** Ordenação de Dijkstra (1965) no `SELECT FOR UPDATE`, tabela desacoplada de idempotência com TTL, classificação automática de lucros isentos (LC 123/2006) e validação de saldo livre antes de estornos para evitar saldo negativo forçado.
