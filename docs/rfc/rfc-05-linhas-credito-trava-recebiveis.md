# RFC 05 — Linhas de Crédito MEI: Antecipação de Recebíveis e Capital de Giro (CCB) com Trava Dinâmica

| | |
|---|---|
| **Status** | **Proposta** |
| **Time** | Core Banking & Crédito |
| **Data** | 21/09/2026 |
| **Versão** | 1.0 |

---

## Contextualização

### Entendendo o problema

O Microempreendedor Individual (MEI) enfrenta uma das maiores barreiras do sistema financeiro nacional: a falta de acesso a crédito acessível. Grandes bancos tradicionais exigem garantias reais pesadas ou cobram juros extorsivos (chegando a ultrapassar 12% a 15% ao mês em cheque especial ou cartão PJ) pela falta de visibilidade do faturamento real do MEI.

Ao mesmo tempo, para a fintech, emprestar dinheiro para MEIs sem uma estrutura adequada de garantias e travas acarreta índices de inadimplência proibitivos (frequentemente superiores a 20% no crédito fumaça tradicional).

Para viabilizar uma carteira de crédito sustentável, rentável e segura para ambas as partes, a arquitetura do CoreBank MEI precisa:
1. Oferecer **Antecipação de Recebíveis** imediata sobre vendas a prazo com colateral garantido pelo próprio fluxo de liquidação futura;
2. Estruturar **Cédulas de Crédito Bancário (CCBs)** de Capital de Giro através da infraestrutura de BaaS da QI Tech SCD;
3. Mitigar o risco de inadimplência através de uma **Trava de Recebíveis Dinâmica**: retenção automática e contínua de uma fração percentual (ex: 15%) de cada venda (PIX/Boleto/Cartão) em um subenvelope (`Pocket`) dedicado à amortização da parcela;
4. Executar **Garantia Cruzada Patrimonial PF/PJ**: alavancar o vínculo unificado entre `BusinessAccount` e `PersonalAccount` do mesmo `Customer`, respaldada pela responsabilidade legal ilimitada do MEI perante o Código Civil.

### Explicando a solução de forma macro

A solução estabelece a esteira de crédito do MEI em duas fases complementares:
1. **Antecipação de Recebíveis (`POST /credit/anticipations`)**:
   - O MEI seleciona cobranças ou parcelas futuras de vendas com cartão/boleto ainda a vencer.
   - O sistema calcula a taxa de desconto (ex: 1,99% a 2,49% a.m.) pró-rata pelos dias de antecipação.
   - Na contratação, o valor líquido é creditado imediatamente na `BusinessAccount` com contrapartida na conta de antecipação da instituição. Quando a adquirente liquida a venda original no futuro, o valor quita a operação automaticamente.
2. **Capital de Giro via CCB Digital (`POST /credit/contracts`)**:
   - O motor de crédito consulta o histórico de faturamento consolidado no `RevenueTracker` e o score salvo no `CustomerRiskProfile` da [RFC 03](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/rfc/rfc-03-onboarding-antifraude-estados.md).
   - Com limite aprovado, a minuta da CCB é emitida via QI Tech SCD com taxa entre 2,89% e 4,5% a.m., parcelada em até 24 meses.
   - O MEI assina eletronicamente com seu `TransactionPin` de 4 dígitos.
   - Os fundos são liberados na `BusinessAccount` em transação de partidas dobradas.
3. **Mecanismo da Trava de Recebíveis Dinâmica (Retenção em Pocket)**:
   - A cada recebimento liquidado na `BusinessAccount`, o sistema desvia atomicamente o percentual pactuado (ex: 15%) para o `Pocket` de código `AMORTIZATION_RESERVE`.
   - Quando o saldo do `Pocket` atinge o valor da parcela vincenda, o split é suspenso. No dia do vencimento, o sistema debita o `Pocket` e liquida a parcela da CCB sem gerar atrito de cobrança manual.
4. **Acionamento de Garantia Cruzada PF/PJ**:
   - Caso o MEI passe do vencimento sem faturamento suficiente na PJ para cobrir a parcela, após 5 dias úteis de tolerância o sistema executa a compensação contábil debitando a `PersonalAccount` vinculada ao mesmo titular.

### Alternativas Descartadas e Trade-offs

- *Empréstimo pessoal tradicional sem garantia nem retenção no fluxo de caixa (Crédito Fumaça)* — descartada pelo alto índice de perda por inadimplência em MEIs sem formalidade fiscal. Ganharia apenas em cenários com taxas de juros abusivas que desvirtuam a proposta de valor do produto.
- *Exigir registro formal de trava de domicílio em registradora autorizada (CERC/B3) para todas as operações* — descartada para microantecipações de baixo valor devido ao custo fixo regulatório de registro por contrato cobrado pelas registradoras. O registro em registradora é reservado apenas para CCBs de valores mais elevados (> R$ 10.000,00).
- *Executar cobrança forçada na PersonalAccount imediatamente no primeiro minuto de atraso* — descartada para evitar atrito desnecessário e litígios; o modelo adota régua de notificação transparente e janela de tolerância de 5 dias úteis antes da compensação cruzada.

---

## Implementação

### Diretriz Obrigatória de Testes
> [!IMPORTANT]
> **Padrão do Projeto: Apenas Testes de Integração (Sem Testes Unitários)**
> Conforme o [ADR-0001](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0001-apenas-testes-de-integracao.md), todos os fluxos de cálculo de juros, amortização em pocket, retenção automática e compensação cruzada devem ser validados exclusivamente via testes de integração ponta a ponta com banco real.

---

### Rotas Propostas

| Método | Caminho | O que faz | Entrada (campos que importam) | Saídas (status e quando) |
|---|---|---|---|---|
| `POST` | `/credit/simulations` | Simula parcelas, juros e margem para CCB ou antecipação | `account_key`, `product_type` (`WORKING_CAPITAL_CCB`, `RECEIVABLES_ANTICIPATION`), `requested_amount_cents`, `installments` | `200 OK` com simulação detalhada (CET, taxa mensal, valor da parcela, % de trava sugerido); `400` valor fora das faixas permitidas |
| `POST` | `/credit/contracts` | Formaliza e contrata CCB de Capital de Giro | `account_key`, `simulation_id`, `transaction_pin`, cabeçalho `Idempotency-Key` | `201 Created` com `contract_key`, link do instrumento da CCB e status `disbursed`; `401` PIN incorreto; `409` proposta expirada |
| `POST` | `/credit/anticipations` | Contrata antecipação de recebíveis futuros de vendas | `account_key`, `charge_keys` (lista de cobranças a antecipar), `transaction_pin` | `201 Created` com `anticipation_key`, valor líquido creditado e taxas retidas; `422` cobrança inelegível |
| `GET` | `/credit/contracts/{contract_key}` | Consulta contrato de crédito, parcelas e saldo devedor | `contract_key` no caminho | `200 OK` detalhes do contrato, parcelas pagas, parcelas em aberto e saldo acumulado no Pocket de amortização |
| `POST` | `/credit/contracts/{contract_key}/repay` | Realiza amortização extraordinária ou quitação antecipada | `contract_key`, `amount_cents`, `transaction_pin` | `200 OK` quitação processada com desconto proporcional de juros futuros |

---

### Banco de Dados (Diagrama ER)

```mermaid
erDiagram
    ACCOUNT ||--o{ CREDIT_CONTRACT : "contrata emprestimos"
    CREDIT_CONTRACT ||--|{ CREDIT_INSTALLMENT : "possui parcelas"
    CREDIT_CONTRACT_STATUS ||--o{ CREDIT_CONTRACT : "estado do contrato"
    ACCOUNT ||--o{ POCKET : "possui subcontas de retencao"
    CREDIT_CONTRACT ||--o{ RECEIVABLES_ANTICIPATION : "pode originar"

    CREDIT_CONTRACT {
        int id PK "interno"
        char contract_key UK "UUIDv4 publico"
        int account_id FK "referencia account(id)"
        int status_id FK "referencia credit_contract_status(id)"
        varchar product_type "WORKING_CAPITAL_CCB, RECEIVABLES_ANTICIPATION"
        bigint principal_amount_cents "Valor principal desembolsado"
        bigint total_amount_cents "Valor total com juros"
        bigint outstanding_balance_cents "Saldo devedor atual"
        decimal interest_rate_monthly "Taxa de juros mensal (ex: 0.0350 = 3.5%)"
        int retention_percentage "Percentual da trava de recebiveis (ex: 15)"
        int installments_count "Numero total de parcelas"
        varchar external_ccb_id "ID do contrato na QI Tech SCD"
        timestamp disbursed_at
        timestamp created_at
    }

    CREDIT_INSTALLMENT {
        int id PK "interno"
        int contract_id FK "referencia credit_contract(id)"
        int installment_number "Numero sequencial da parcela"
        bigint amount_cents "Valor total da parcela"
        bigint principal_cents "Amortizacao do principal"
        bigint interest_cents "Juros remuneratorios"
        date due_date "Data de vencimento"
        varchar status "PENDING, PAID, OVERDUE, WAIVED"
        timestamp settled_at
    }

    CREDIT_CONTRACT_STATUS {
        int id PK
        varchar enumerator UK "simulated, pending_signature, disbursed, active, settled, in_default, cancelled"
        varchar description
    }

    RECEIVABLES_ANTICIPATION {
        int id PK
        char anticipation_key UK "UUIDv4"
        int account_id FK
        bigint gross_amount_cents "Valor bruto a receber no futuro"
        bigint net_amount_cents "Valor liquido antecipado hoje"
        bigint discount_fee_cents "Taxa de desconto retida"
        timestamp anticipated_at
    }
```

---

### Desenho de Fluxo da Trava Dinâmica de Recebíveis e Amortização em Pocket

```mermaid
flowchart TD
    START((Recebimento Liquidado na Conta PJ)) --> CHECK_ACTIVE_CREDIT{"Possui contrato ativo com trava de recebíveis?"}
    
    CHECK_ACTIVE_CREDIT -- "Não" --> REGULAR_CREDIT["Saldo líquido 100% disponível para uso do MEI"]
    
    CHECK_ACTIVE_CREDIT -- "Sim" --> CHECK_INSTALLMENT_TARGET{"Pocket de amortização atingiu o valor da parcela do mês?"}
    
    CHECK_INSTALLMENT_TARGET -- "Sim" --> REGULAR_CREDIT
    
    CHECK_INSTALLMENT_TARGET -- "Não" --> CALC_SPLIT["Calcular valor da retenção:<br/>retention_cents = amount_cents * (retention_percentage / 100)"]
    
    CALC_SPLIT --> ATOMIC_TRANSFER["Transação Atômica no Ledger:<br/>1. DÉBITO BusinessAccount / CRÉDITO Pocket 'AMORTIZATION_RESERVE'<br/>2. Atualizar saldo acumulado da parcela"]
    
    ATOMIC_TRANSFER --> CHECK_DUE_DATE{"Hoje é o dia do vencimento da parcela?"}
    
    CHECK_DUE_DATE -- "Sim" --> LIQUIDATE_INSTALLMENT["Transação Atômica de Quitação:<br/>1. DÉBITO Pocket 'AMORTIZATION_RESERVE' / CRÉDITO SettlementAccount da CCB<br/>2. Marcar credit_installment.status = 'PAID'<br/>3. Reduzir saldo devedor principal do contrato"]
    
    CHECK_DUE_DATE -- "Não" --> WAIT_DUE_DATE((Saldo permanece retido aguardando o vencimento))
    
    LIQUIDATE_INSTALLMENT --> SUCCESS((Parcela Liquidada Automaticamente sem Inadimplência))

    style SUCCESS fill:#c8e6c9,color:#1b5e20,stroke:#1b5e20
    style REGULAR_CREDIT fill:#e0f2f1,color:#004d40,stroke:#004d40
    style START fill:#e0f2f1,color:#004d40,stroke:#004d40
```

---

### Desenho de Fluxo da Garantia Cruzada PF/PJ em Atraso

```mermaid
flowchart TD
    TRIGGER((Parcela Vencida há 5 dias úteis)) --> CHECK_PJ_BALANCE{"Conta PJ tem saldo suficiente?"}
    
    CHECK_PJ_BALANCE -- "Sim" --> DEBIT_PJ["Débito automático na BusinessAccount e liquidação da parcela"]
    
    CHECK_PJ_BALANCE -- "Não" --> CHECK_PF_BALANCE{"Conta PF (PersonalAccount) tem saldo disponível?"}
    
    CHECK_PF_BALANCE -- "Não" --> MARK_DEFAULT["Marcar contrato como 'in_default'<br/>Acionar régua de cobrança digital e notificação Serasa"]
    
    CHECK_PF_BALANCE -- "Sim" --> DEBIT_CROSS["Compensação Patrimonial Cruzada (Art. 368 Código Civil):<br/>1. DÉBITO PersonalAccount (CPF)<br/>2. CRÉDITO SettlementAccount da CCB<br/>3. Gravar justificativa formal: 'CROSS_GUARANTEE_MEI_SETTLEMENT'"]
    
    DEBIT_CROSS --> NOTIFY_CUSTOMER["Disparar notificação imediata ao MEI informando a compensação cruzada"]
    NOTIFY_CUSTOMER --> DONE((Parcela Quitada com Sucesso))

    style DONE fill:#c8e6c9,color:#1b5e20,stroke:#1b5e20
    style MARK_DEFAULT fill:#ffcdd2,color:#b71c1c,stroke:#b71c1c
    style TRIGGER fill:#fff9c4,color:#f57f17,stroke:#f57f17
```

---

## Principal Desafio

- **Qual é:** Conciliação determinística da trava de recebíveis concorrente com movimentações operacionais do MEI, garantindo que o split nunca bloqueie mais recursos do que o estritamente contratado para a parcela do mês.
- **Por que é difícil:** Se o MEI recebe dezenas de transações PIX e boletos em curto intervalo de tempo em horário de pico, múltiplas transações concorrentes tentam calcular e debitar para o `Pocket`. Sem controle adequado de contenção, o `Pocket` poderia acumular mais do que o valor da parcela ou gerar contenção severa de locks de linha.
- **Como o desenho resolve:** Utilização de lock pessimista na linha do `Pocket` e verificação do teto da parcela dentro da mesma transação de liquidação da cobrança com ordenação de Dijkstra ([ADR-0002](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0002-prevencao-deadlock-ordenacao-dijkstra.md)), garantindo que a soma acumulada nunca exceda a meta da parcela.
