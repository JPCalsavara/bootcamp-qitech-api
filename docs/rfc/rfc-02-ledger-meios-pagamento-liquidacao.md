# RFC 02 — Motor Financeiro, Ledger de Partidas Dobradas, Meios de Pagamento e Liquidação Transacional

| | |
|---|---|
| **Status** | **Aprovada / Parcialmente Implementada** |
| **Time** | Core Banking, Transações & Pagamentos |
| **Data** | 23/09/2026 |
| **Versão** | 1.0 (Consolidação Unificada das RFCs 02 e 04) |

> [!NOTE]
> **Grau de Maturidade e Roadmap**:
> - **Implementado em Código**: Motor financeiro central de partidas dobradas ([ADR-0004](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0004-arquitetura-contabil-partidas-dobradas.md)), representação monetária estrita em centavos inteiros `BIGINT` ([ADR-0003](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0003-representacao-monetaria-centavos-bigint.md)), hierarquia de locks de Dijkstra contra deadlocks ([ADR-0002](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0002-prevencao-deadlock-ordenacao-dijkstra.md)), tabela de idempotência com TTL de 24h ([ADR-0006](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0006-idempotencia-tabela-dedicada-catalogo-erros.md)), classificação contábil da LC 123/2006 (`PROFIT_DISTRIBUTION`) e política estrita de estornos.
> - **Roadmap / Em Refinamento**: Emissão de cobranças multimodais (`Charge` via PIX QR Code dinâmico, Boleto Híbrido e Link), ingestão de webhooks com assinatura HMAC SHA-256 e tarifação transacional automática em partidas dobradas com crédito em `FeeRevenueAccount` ([ADR-0008](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0008-tarifacao-transacional-debito-atomico-ledger.md)).

---

## Contextualização

### Entendendo o problema

No núcleo de uma instituição financeira voltada a microempreendedores, o processamento transacional e as cobranças comerciais exigem requisitos inegociáveis de precisão contábil, segurança cibernética e clareza fiscal:

1. **Precisão Contábil e Auditoria Forense**: O saldo bancário nunca é uma coluna arbitrária sujeita a updates pontuais sem lastro. Toda e qualquer movimentação de recursos deve ser fundamentada por um livro-razão (*ledger*) de partidas dobradas (*double-entry*), no qual a soma algébrica de créditos e débitos de qualquer evento financeiro é rigorosamente zero ([ADR-0004](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0004-arquitetura-contabil-partidas-dobradas.md)).
2. **Prevenção Matemática de Deadlocks sob Alta Concorrência**: Transações simultâneas e cruzadas entre múltiplas contas no mesmo milissegundo adquirem travas de linha (`SELECT FOR UPDATE`) em ordens contrárias, provocando deadlocks no banco de dados (`40P01`) e derrubando requisições se não houver ordenação determinística ([ADR-0002](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0002-prevencao-deadlock-ordenacao-dijkstra.md)).
3. **Idempotência Resiliente com TTL**: Instabilidades de rede móvel provocam retentativas repetidas de clientes e parceiros externos. É indispensável gerenciar a idempotência em tabela dedicada com expiração de 24 horas, gravando tanto respostas de sucesso quanto de falha de validação ([ADR-0006](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0006-idempotencia-tabela-dedicada-catalogo-erros.md)).
4. **Segurança de Execução (PIN Transacional)**: O token de login (JWT) não pode conceder autorização irrestrita de débito; transferências exigem confirmação pelo **PIN Transacional de 4 dígitos** do titular.
5. **Enquadramento Fiscal MEI (Art. 14 da LC 123/2006)**: Movimentações da `BusinessAccount` para a `PersonalAccount` do mesmo MEI caracterizam distribuição isenta de lucros e devem ser etiquetadas nativamente no ledger (`PROFIT_DISTRIBUTION`) para subsidiar a declaração anual do IRPF.
6. **Cobrança Comercial e o Risco do Extrato Líquido**: Quando gateways tradicionais abatem as tarifas diretamente do valor creditado (ex: venda de R$ 100,00 entra líquida como R$ 96,01), o MEI enfrenta sérios problemas com a Receita Federal, pois sua Nota Fiscal (NFS-e) e o limite anual de R$ 81.000,00 exigem a comprovação do **faturamento bruto**.
7. **Ausência de Partidas Dobradas na Tarifação**: Tarifas deduzidas de forma opaca como "ajustes manuais" geram furos de conciliação. Toda tarifa cobrada deve ser formalizada como transferência atômica para a conta interna de receita (`FeeRevenueAccount`) ([ADR-0008](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0008-tarifacao-transacional-debito-atomico-ledger.md)).

### Explicando a solução de forma macro

A solução combina o motor contábil de transferências com a esteira de cobranças comerciais e liquidação de webhooks:

1. **Ledger Imutável de Partidas Dobradas ([ADR-0004](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0004-arquitetura-contabil-partidas-dobradas.md))**:
   - A tabela `ledger_entry` é estritamente *append-only*.
   - Toda transação insere atomicamente um registro de `DEBIT` e um registro de `CREDIT` de mesmo valor em centavos inteiros (`BIGINT`) ([ADR-0003](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0003-representacao-monetaria-centavos-bigint.md)), atualizando o campo `balance_after_cents` para auditoria imediata.
2. **Ordenação Determinística de Dijkstra ([ADR-0002](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0002-prevencao-deadlock-ordenacao-dijkstra.md))**:
   - Antes de adquirir locks de linha via `SELECT FOR UPDATE`, a aplicação ordena os identificadores inteiros das contas envolvidas (`sorted([account_a_id, account_b_id, ...])`). A espera circular torna-se matematicamente impossível.
3. **Idempotência com Tabela Dedicada (`idempotency_record`) ([ADR-0006](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0006-idempotencia-tabela-dedicada-catalogo-erros.md))**:
   - Chave enviada no cabeçalho `Idempotency-Key` é confrontada com o hash SHA-256 do payload. Retentativas recebem a resposta do cache sem reprocessamento. Disparos concorrentes com mesmo payload sofrem contenção e requisições com chave idêntica mas payload diferente recebem `409 Conflict` (`QIT001008`).
4. **Mecânica Estrita de Estornos (`reversed`)**:
   - O estorno gera lançamentos de contrapartida invertidos e exige validação de saldo livre na conta recebedora original (`available_balance_cents >= original_amount`). Se a conta não tiver fundos disponíveis suficientes, o estorno é recusado com erro semântico, impedindo saldo negativo desautorizado.
5. **Emissão de Cobranças Multimodais (`POST /accounts/{account_key}/charges`)**:
   - Suporte a **PIX Cobrança** (QR Code dinâmico e `txid` registrado no SPI via BaaS QI Tech), **Boleto Híbrido** (código de barras Febraban + QR Code PIX no mesmo título) e **Link de Pagamento** para cartão de crédito.
6. **Ingestão Resiliente de Webhooks e Tarifação Atômica ([ADR-0008](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0008-tarifacao-transacional-debito-atomico-ledger.md))**:
   - Webhooks de parceiros adquirentes/BaaS são autenticados via assinatura HMAC (`X-Signature-SHA256`) e registrados imediatamente na tabela `webhook_event`.
   - Na liquidação contábil, uma transação única executa:
     - **Crédito Bruto**: Débito em `SettlementAccount` / Crédito na `BusinessAccount` do MEI (valor integral da venda).
     - **Tarifação Atômica**: Débito na `BusinessAccount` / Crédito na conta interna de receita `FeeRevenueAccount` (tarifa transacional pactuada).
     - **Atualização Fiscal**: Acúmulo do faturamento bruto no `RevenueTracker` para governança do teto do MEI (R$ 81k).

### Alternativas Descartadas e Trade-offs

- *Idempotência controlada apenas como coluna única na tabela `transaction`* — descartada porque não permitiria reter e devolver respostas cacheadas de falha de validação ou erros de negócio antes da criação do registro financeiro, além de impedir o lock distribuído de requisições em voo.
- *Liquidação líquida direta (Net Settlement)* — creditar o valor da venda já deduzido da comissão/tarifa: descartada porque viola a transparência contábil, prejudica a emissão da NFS-e pelo MEI e esconde a receita transacional da instituição bancária.
- *Permitir saldo negativo em estornos forçados (Overdraft compulsório)* — descartada por compliance bancário e proteção contra inadimplência: sem contrato formal de limite de crédito garantido, a instituição financeira assume risco indevido caso o cliente recebedor já tenha sacado os recursos.
- *Valores monetários representados com números de ponto flutuante (`FLOAT`/`DOUBLE`)* — **descartada conforme [ADR-0003](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0003-representacao-monetaria-centavos-bigint.md)**: dízimas e imprecisões de arredondamento inerentes à norma IEEE 754 violam a exatidão centesimal do ledger.

---

## Implementação

### Diretriz Obrigatória de Testes
> [!IMPORTANT]
> **Padrão do Projeto: Apenas Testes de Integração (Sem Testes Unitários)**
> Conforme o [ADR-0001](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0001-apenas-testes-de-integracao.md), todo o motor financeiro e a esteira de cobrança devem ser cobertos exclusivamente por testes de integração ponta a ponta (`tests/integration/`), testando concorrência real via múltiplas conexões simultâneas no banco de dados PostgreSQL.

---

### Rotas Propostas

| Método | Caminho | O que faz | Entrada (campos que importam) | Saídas (status e quando) |
|---|---|---|---|---|
| `POST` | `/transactions/transfers` | Executa transferência bilateral atômica, validando PIN e idempotência | `origin_account_key`, `destination_account_key`, `amount_cents`, `description`, `transaction_pin`, cabeçalho `Idempotency-Key` | `201 Created` liquidada com `transaction_key` e `end_to_end_id`; `400` payload inválido (`QIT000001`); `401` PIN inválido (`QIT000402`); `404` conta não encontrada (`QIT001001`); `409` conflito de idempotência (`QIT001008`) ou conta de origem bloqueada/inativa (`QIT001009`); `422` saldo insuficiente (`QIT001010`) |
| `POST` | `/transactions/{transaction_key}/reversals` | Executa estorno contábil bilateral de uma transação liquidada | `reason`, `transaction_pin`, cabeçalho `Idempotency-Key` | `201 Created` estorno liquidado com nova transação de contrapartida; `401` PIN incorreto; `404` transação original não encontrada; `409` transação já estornada; `422` saldo insuficiente na conta recebedora (`QIT001012`) |
| `GET` | `/transactions/{transaction_key}` | Consulta detalhes, lançamentos e status de uma transação | `transaction_key` no caminho | `200 OK` detalhes da transação, contas, valor, tipo contábil/fiscal e status; `404` transação não encontrada |
| `GET` | `/accounts/{account_key}/statement` | Emite extrato de lançamentos contábeis enriquecido e paginado | `account_key` no caminho, `limit`, `page`, `start_date`, `end_date` | `200 OK` extrato contendo contraparte (nome/documento), classificação fiscal (`PROFIT_DISTRIBUTION`, `TRANSFER`, etc.), valor e `balance_after_cents`; `404` conta não encontrada |
| `POST` | `/accounts/{account_key}/charges` | Emite cobrança comercial (PIX dinâmico, Boleto Híbrido ou Link) | `method` (`PIX`, `BOLETO_HYBRID`, `PAYMENT_LINK`), `amount_cents`, `due_date`, `customer_document`, `metadata` | `201 Created` com `charge_key`, dados de pagamento (`qr_code`, `barcode`, `payment_url`), valor facial e vencimento; `404` conta não encontrada; `422` conta não é do tipo BUSINESS |
| `GET` | `/charges/{charge_key}` | Consulta situação da cobrança e dados de liquidação | `charge_key` no caminho | `200 OK` detalhes da cobrança, status (`pending`, `settled`, `expired`, `cancelled`), valores bruto e taxas retidas; `404` cobrança não encontrada |
| `POST` | `/webhooks/payments` | Ingestão e liquidação em tempo real de webhooks de parceiros BaaS/Adquirentes | Payload bruto do evento, cabeçalho de assinatura `X-Signature-SHA256` | `200 OK` recebido e liquidado com crédito bruto e tarifação atômica; `401` assinatura HMAC inválida; `404` cobrança não localizada |
| `POST` | `/charges/reconciliation` | Job periódico de conciliação ativa (Polling HTTP via conector de pagamentos) | Opcional: lista de `charge_keys` a conciliar ou varredura de pendências | `200 OK` total de cobranças conciliadas e atualizadas no ledger |

---

### Banco de Dados (Diagrama ER Unificado)

```mermaid
erDiagram
    ACCOUNT ||--o{ TRANSACTION : "origina debito"
    ACCOUNT ||--o{ TRANSACTION : "recebe credito"
    ACCOUNT ||--o{ LEDGER_ENTRY : "possui lancamentos"
    ACCOUNT ||--o{ CHARGE : "emite cobrancas (BUSINESS)"

    TRANSACTION_STATUS ||--o{ TRANSACTION : "define estado"
    TRANSACTION ||--o{ TRANSACTION_STATUS_EVENT : "gera historico auditavel"
    TRANSACTION_STATUS ||--o{ TRANSACTION_STATUS_EVENT : "define de/para"

    TRANSACTION ||--|{ LEDGER_ENTRY : "origina partidas dobradas (D e C)"
    IDEMPOTENCY_RECORD ||--o| TRANSACTION : "assegura unicidade de chamada"

    CHARGE_METHOD ||--o{ CHARGE : "modalidade"
    CHARGE_STATUS ||--o{ CHARGE : "ciclo de vida"
    CHARGE ||--o{ WEBHOOK_EVENT : "notificado por"
    CHARGE ||--o| TRANSACTION : "liquidado por"

    ACCOUNT {
        int id PK "interno"
        char account_key UK "UUIDv4 publico (ADR-0005)"
        int status_id FK
        string account_type "BUSINESS ou PERSONAL"
        bigint balance_cents "Saldo total (CHECK >= 0)"
        bigint blocked_balance_cents "Saldo bloqueado MED (CHECK >= 0)"
    }

    TRANSACTION_STATUS {
        int id PK
        string enumerator UK "pending, settled, failed, reversed"
        datetime created_at
    }

    TRANSACTION {
        int id PK "interno autoincrement"
        char transaction_key UK "UUIDv4 publico (ADR-0005)"
        string end_to_end_id UK "Rastreabilidade BACEN"
        int origin_account_id FK "Conta debitada"
        int destination_account_id FK "Conta creditada"
        int status_id FK "referencia transaction_status(id)"
        string transaction_type "TRANSFER, PROFIT_DISTRIBUTION, DEPOSIT, REVERSAL, FEE_DEBIT, CHARGE_SETTLEMENT, CREDIT_DISBURSEMENT"
        bigint amount_cents "Valor em centavos inteiros (CHECK > 0)"
        string description "Descricao da operacao"
        int reversal_of_transaction_id FK "Origem em caso de estorno"
        datetime created_at
    }

    TRANSACTION_STATUS_EVENT {
        int id PK
        int transaction_id FK
        int from_status_id FK
        int to_status_id FK
        string reason "Motivo da mudanca"
        datetime event_datetime
        datetime created_at "append-only imutavel"
    }

    LEDGER_ENTRY {
        int id PK "interno autoincrement"
        int account_id FK "Conta afetada"
        int transaction_id FK "Transacao originadora"
        string entry_type "DEBIT ou CREDIT"
        bigint amount_cents "Valor absoluto em centavos inteiros"
        bigint balance_after_cents "Saldo resultante imediatamente apos o lancamento"
        datetime created_at "append-only imutavel"
    }

    IDEMPOTENCY_RECORD {
        int id PK
        string idempotency_key UK "Chave do cliente (ADR-0006)"
        string request_path "URI da chamada"
        string request_hash "Hash SHA-256 do payload"
        int response_code "Status HTTP gravado"
        string response_body "Resposta salva em cache"
        datetime expires_at "TTL de 24 horas"
        datetime created_at
    }

    CHARGE {
        int id PK "interno"
        char charge_key UK "UUIDv4 publico"
        int account_id FK "BusinessAccount emissora"
        int method_id FK "referencia charge_method(id)"
        int status_id FK "referencia charge_status(id)"
        int settlement_transaction_id FK "referencia transaction(id)"
        bigint amount_cents "Valor facial da cobranca"
        bigint fee_cents "Tarifa acordada de intermediacao"
        string external_reference UK "txid do PIX ou nosso_numero"
        datetime due_date "Vencimento"
        jsonb metadata "Dados do sacado e cobranca"
        datetime created_at
        datetime settled_at
    }

    CHARGE_METHOD {
        int id PK
        string enumerator UK "PIX, BOLETO_HYBRID, PAYMENT_LINK, DEBIT_CARD"
        string description
    }

    CHARGE_STATUS {
        int id PK
        string enumerator UK "pending, settled, expired, cancelled, refunded"
        string description
    }

    WEBHOOK_EVENT {
        int id PK
        char event_key UK "UUIDv4"
        string provider "QITECH, ADYEN, PAGSEGURO"
        string event_type "PIX_RECEIVED, BOLETO_PAID, CARD_CAPTURED"
        jsonb payload "Payload bruto recebido"
        string signature "Assinatura HMAC recebida"
        string status "received, processed, failed"
        datetime received_at
        datetime processed_at
    }
```

---

### Desenho de Fluxo da Rota (As Seis Perguntas Respondidas no Desenho)

#### Fluxo 1: `POST /transactions/transfers` — Execução com Validação de PIN, Dijkstra e Partidas Dobradas

```mermaid
flowchart TD
    START((Início: POST /transfers)) --> CHECK_IDEM["1. Verificar idempotency_record pela Idempotency-Key"]
    CHECK_IDEM --> HAS_IDEM{"Chave já existe?"}
    
    HAS_IDEM -- "Sim" --> CHECK_HASH{"Mesmo request_hash?"}
    CHECK_HASH -- "Sim" --> RETURN_CACHE["Retornar resposta em cache (sem reprocessar)"]
    RETURN_CACHE --> END_CACHE((Success/Error Cache))
    CHECK_HASH -- "Não" --> ERR_409_IDEM["Error (409 QIT001008 - Conflito de Idempotência)"]
    
    HAS_IDEM -- "Não" --> VALIDATE_PIN["2. Validar transaction_pin contra pin_hash do Customer"]
    VALIDATE_PIN --> PIN_OK{"PIN correto?"}
    
    PIN_OK -- "Não (401)" --> ERR_401["Error (401 QIT000402 - PIN Inválido)"]
    PIN_OK -- "Sim" --> LOCK_ACCOUNTS["3. Adquirir locks ordenados (ADR-0002 Dijkstra):<br/>sorted([origin_id, destination_id]) com SELECT FOR UPDATE"]
    
    LOCK_ACCOUNTS --> ACCOUNTS_EXIST{"Ambas as contas existem?"}
    ACCOUNTS_EXIST -- "Não (404)" --> ERR_404["Error (404 QIT001001)"]
    ACCOUNTS_EXIST -- "Sim" --> CHECK_ACTIVE{"Origem ativa? Destino apto a receber crédito?"}
    
    CHECK_ACTIVE -- "Não (409)" --> ERR_INACTIVE["Error (409 QIT001009 - Conta Inativa/Bloqueada para Débito)"]
    CHECK_ACTIVE -- "Sim" --> CHECK_BALANCE{"Origem tem saldo livre?<br/>balance_cents - blocked_balance_cents >= amount_cents"}
    
    CHECK_BALANCE -- "Não (422)" --> ERR_FUNDS["Error (422 QIT001010 - Saldo Disponível Insuficiente)"]
    CHECK_BALANCE -- "Sim" --> CHECK_FISCAL{"Origem é PJ e Destino é PF do mesmo titular?"}
    
    CHECK_FISCAL -- "Sim" --> SET_PROFIT["transaction_type = PROFIT_DISTRIBUTION (Art. 14 LC 123)"]
    CHECK_FISCAL -- "Não" --> SET_TRANSFER["transaction_type = TRANSFER"]
    
    SET_PROFIT --> ATOMIC_TX
    SET_TRANSFER --> ATOMIC_TX
    
    ATOMIC_TX["4. Transação Atômica no PostgreSQL:<br/>- Inserir Transaction (status: 'settled')<br/>- Inserir LedgerEntry DEBIT na origem (com balance_after_cents)<br/>- Inserir LedgerEntry CREDIT no destino (com balance_after_cents)<br/>- Atualizar saldos em account<br/>- Gravar idempotency_record com TTL 24h"]
    
    ATOMIC_TX --> BUILD_DTO["5. Montar DTO enriquecido com transaction_key e end_to_end_id"]
    BUILD_DTO -- "201 Created" --> SUCCESS((Success 201 Created))

    style ERR_409_IDEM fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_401 fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_404 fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_INACTIVE fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ERR_FUNDS fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style SUCCESS fill:#c8e6c9,color:#1b5e20,stroke:#1b5e20
    style START fill:#e0f2f1,color:#004d40,stroke:#004d40
    style ATOMIC_TX fill:#e1f5fe,color:#01579b,stroke:#0288d1
```

#### Fluxo 2: Ingestão de Webhook e Liquidação com Débito Atômico de Tarifa ([ADR-0008](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0008-tarifacao-transacional-debito-atomico-ledger.md))

```mermaid
flowchart TD
    WEBHOOK_IN((Webhook Recebido)) --> VERIFY_SIG["1. Validar Assinatura HMAC (X-Signature-SHA256)"]
    VERIFY_SIG --> IS_SIG_OK{"Assinatura válida?"}
    
    IS_SIG_OK -- "Não (401)" --> ERR_401_SIG["Error (401 Unauthorized)"]
    IS_SIG_OK -- "Sim" --> RECORD_WEBHOOK["2. Inserir webhook_event (status: 'received')"]
    
    RECORD_WEBHOOK --> ACK_HTTP["3. Responder HTTP 200 OK imediatamente ao parceiro"]
    ACK_HTTP --> LOCK_TRIPARTITE["4. Ordenar IDs de contas e travar (Dijkstra):<br/>sorted([settlement_account_id, business_account_id, fee_revenue_account_id])"]
    
    LOCK_TRIPARTITE --> CHECK_CHARGE{"Cobrança já liquidada?"}
    CHECK_CHARGE -- "Sim" --> IGNORE_DUP["Ignorar duplicidade (Idempotente)"]
    
    CHECK_CHARGE -- "Não" --> ATOMIC_SETTLE["5. Transação Atômica no Ledger:<br/>- Lançamento Bruto: DÉBITO SettlementAccount / CRÉDITO BusinessAccount<br/>- Tarifação Atômica: DÉBITO BusinessAccount / CRÉDITO FeeRevenueAccount<br/>- Atualizar RevenueTracker com o valor bruto da venda<br/>- Atualizar charge.status para 'settled'"]
    
    ATOMIC_SETTLE --> FINISH_SETTLE((Liquidação e Tarifação Concluídas))

    style ERR_401_SIG fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style ACK_HTTP fill:#c8e6c9,color:#1b5e20,stroke:#1b5e20
    style FINISH_SETTLE fill:#c8e6c9,color:#1b5e20,stroke:#1b5e20
    style WEBHOOK_IN fill:#e0f2f1,color:#004d40,stroke:#004d40
    style ATOMIC_SETTLE fill:#e1f5fe,color:#01579b,stroke:#0288d1
```

---

### Fluxos Detalhados Textuais

#### Fluxo 1: Caminho Feliz de Transferência e Estorno
1. **Transferência**: O cliente envia `POST /transactions/transfers` com chave de idempotência e PIN. O controller valida o PIN via Argon2id, adquire locks ordenados, valida saldo livre e insere a transação no ledger com partidas dobradas, devolvendo `201 Created` e gravando o cache de idempotência.
2. **Estorno Contábil**: O titular solicita `POST /transactions/{transaction_key}/reversals`. O sistema localiza a transação original, adquire travas ordenadas nas duas contas e verifica se a conta recebedora possui saldo disponível suficiente para absorver o débito. Se sim, cria nova transação do tipo `REVERSAL`, atualiza a original para `reversed` e registra as partidas dobradas invertidas no ledger.

#### Fluxo 2: Caminhos de Falha e Exceções Formais
1. **PIN Transacional Incorreto**: Retorna `401 Unauthorized` com código de catálogo `QIT000402` (`INVALID_TRANSACTION_PIN`).
2. **Conflito de Idempotência**: Quando o mesmo cabeçalho `Idempotency-Key` é enviado com payload distinto dentro do intervalo de 24h, retorna `409 Conflict` com código `QIT001008` (`IDEMPOTENCY_PAYLOAD_MISMATCH`).
3. **Saldo Disponível Insuficiente**: Se `available_balance_cents < amount_cents`, a operação é bloqueada com `422 Unprocessable Entity` e código `QIT001010` (`INSUFFICIENT_FUNDS`).
4. **Conta Inativa ou Bloqueada**: Se a conta de origem estiver em estado `blocked` ou `closed`, a tentativa de débito é rejeitada com `409 Conflict` e código `QIT001009` (`ACCOUNT_BLOCKED_FOR_DEBIT`).
5. **Tentativa de Estorno sem Saldo na Contraparte**: Caso a conta recebedora não detenha fundos livres para absorver o débito de retorno, a solicitação falha com `422 Unprocessable Entity` e código `QIT001012` (`INSUFFICIENT_FUNDS_FOR_REVERSAL`).

---

## Principal Desafio

- **Qual é:** Concorrência transacional extrema imune a deadlocks de banco de dados (`40P01`), combinada com a atomicidade irrestrita na liquidação tripartite de cobranças comerciais (crédito bruto ao MEI, débito atômico de taxa de intermediação para a conta da fintech e acúmulo no rastreador fiscal anual).
- **Por que é difícil:** Transferências simultâneas em sentidos opostos entre as mesmas contas disparam contenção imediata de locks. Se os locks forem adquiridos na ordem da requisição, o PostgreSQL aborta uma das transações com erro de deadlock. Além disso, se o crédito bruto e a tarifação fossem executados em transações separadas, instabilidades de rede poderiam creditar a venda sem cobrar a taxa ou permitir que o MEI sacasse os fundos antes da dedução da tarifa.
- **Como o desenho resolve:** Aplicação estrita da ordenação global de Dijkstra (`sorted([acc_a, acc_b, ...])`) antes de qualquer declaração `SELECT FOR UPDATE` ([ADR-0002](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0002-prevencao-deadlock-ordenacao-dijkstra.md)), e execução da liquidação tripartite dentro de uma única transação atômica do banco de dados com lançamentos simétricos no ledger imutável ([ADR-0004](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0004-arquitetura-contabil-partidas-dobradas.md) e [ADR-0008](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0008-tarifacao-transacional-debito-atomico-ledger.md)).
