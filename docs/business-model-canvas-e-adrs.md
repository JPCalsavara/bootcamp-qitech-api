# CoreBank MEI: Business Model Canvas & ADRs de Arquitetura

Este documento consolida a modelagem estratégica de negócio baseada na metodologia oficial do **Business Model Canvas** (Alexander Osterwalder & Yves Pigneur) e o registro das decisões arquiteturais fundamentais (**ADRs**) para o desenvolvimento da API de Core Banking voltada para MEIs e profissionais autônomos.

---

## 1. Visão Geral do Projeto

* **Nome do Produto:** CoreBank MEI
* **Categoria:** API de Core Banking & Ledger Contábil em Tempo Real
* **Público Principal:** Microempreendedores Individuais (MEIs) e Prestadores de Serviços Autônomos (PJ)
* **Objetivo Central:** Oferecer uma infraestrutura de conta de pagamento simples, ágil e matematicamente precisa, eliminando desvios contábeis, tarifas abusivas e riscos de cobranças duplicadas ou inconsistências transacionais.

---

## 2. Business Model Canvas (Poster Oficial)

Baseado nos 9 blocos conceituais do framework do Business Model Canvas:

```
┌─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┐
│ 8. PARCERIAS-CHAVE              │ 7. ATIVIDADES-CHAVE             │ 2. PROPOSTAS DE VALOR           │ 4. RELACIONAMENTO COM CLIENTES  │ 1. SEGMENTOS DE CLIENTES        │
│ (Key Partners)                  │ (Key Activities)                │ (Value Propositions)            │ (Customer Relationships)        │ (Customer Segments)             │
│                                 │                                 │                                 │                                 │                                 │
│ • Provedores de BaaS (QI Tech)  │ • Desenvolvimento e evolução da │ • Conciliação Contábil em Tempo │ • Suporte Digital Automatizado: │ • Microempreendedores           │
│   para conectividade ao SPB/PIX.│   API de Core Banking e Ledger. │   Real: zero centavo perdido    │   Self-service via portal web/  │   Individuais (MEIs) do setor   │
│ • Softwares de Gestão Financeira│ • Gestão de conciliação bancária│   com motor de partidas dobradas│   aplicativo.                   │   de serviços e comércio local. │
│   e ERPs (ex: ContaAzul, Bling).│   e integridade contábil.       │ • Transferências Instantâneas:  │ • Transparência Absoluta:       │ • Profissionais PJ Autônomos:   │
│ • Emissores de Certificados e   │ • Monitoramento de segurança,   │   liquidação atômica e segura   │   notificação clara de eventos  │   desenvolvedores, designers,   │
│   Bureaus de Crédito/KYC.       │   mitigação de fraudes e locks. │   livre de erros de concorrência│   financeiros e extrato detalhado│  consultores, redatores.       │
│ • Contabilidades online parceiras│• Compliance com normas de      │ • Simplicidade Operacional:     │ • Comunidades & Desenvolvedores:│                                 │
│   para indicação mútua.         │   Instituição de Pagamento (IP).│   sem tarifas abusivas ou contas│   documentação Swagger/OpenAPI  │ Early Adopters:                 │
│                                 ├─────────────────────────────────┤   complexas de bancos legado.   │   aberta e sandbox de testes.   │ • Freelancers tech e consultores│
│                                 │ 6. RECURSOS-CHAVE               │ • Resiliência Transacional:     │                                 │   de tecnologia.                │
│                                 │ (Key Resources)                 │   idempotência nativa contra    │                                 │                                 │
│                                 │                                 │   falhas de rede e duplicações. ├─────────────────────────────────┤                                 │
│                                 │ • Motor de Ledger Imutável em   │                                 │ 3. CANAIS                       │                                 │
│                                 │   PostgreSQL com locking seguro.│ Conceito de Alto Nível:         │ (Channels)                      │                                 │
│                                 │ • Stack robusta: Python/FastAPI,│ "A infraestrutura financeira da │                                 │                                 │
│                                 │   SQLAlchemy 2.0 e Docker.      │ Stripe com o rigor contábil de  │ • API REST Direta (B2B/B2B2C).  │                                 │
│                                 │ • Equipe de engenharia focada   │ um core banking para o MEI."    │ • Parcerias de integração com   │                                 │
│                                 │   em sistemas distribuídos/ACID.│                                 │   ERPs e emissores de NF-e.     │                                 │
│                                 │ • Licença e credenciais de BaaS.│                                 │ • Aplicativo Mobile / Web leve. │                                 │
├─────────────────────────────────┴─────────────────────────────────┼─────────────────────────────────┴─────────────────────────────────┼─────────────────────────────────┤
│ 9. ESTRUTURA DE CUSTOS                                            │ 5. FONTES DE RECEITA                                                                                │
│ (Cost Structure)                                                  │ (Revenue Streams)                                                                                   │
│                                                                   │                                                                                                     │
│ • Infraestrutura em Nuvem: banco de dados PostgreSQL relacional   │ • Tarifa Transacional por Liquidação: taxa fixa ou percentual reduzido sobre cobranças recebidas.   │
│   gerenciado com alta disponibilidade e instâncias de API.        │ • Float Financeiro: remuneração de liquidez sobre saldos mantidos em conta de liquidação.            │
│ • Custos de Conectores Externos: taxas por consulta KYC e por     │ • Mensalidade de Recursos Avançados (Freemium): emissão ilimitada de notas e relatórios DRE.        │
│   transação liquidada no SPB/PIX/Boleto.                          │ • Tarifas de Transferências Externas: taxa sobre saques TED/PIX para contas bancárias tradicionais.│
│ • Pessoal e Engenharia: suporte, desenvolvimento e segurança.     │                                                                                                     │
└───────────────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detalhamento dos 9 Blocos do Canvas

### 1. Segmentos de Clientes (Customer Segments)
* **Microempreendedores Individuais (MEIs):** Mais de 15 milhões de profissionais no Brasil que precisam separar o caixa da pessoa física do caixa da empresa sem pagar mensalidades de R$ 50 a R$ 100 em bancos convencionais.
* **Prestadores de Serviços Autônomos (PJ):** Profissionais de tecnologia, saúde, marketing e consultoria que faturam mensalmente por projetos e exigem extratos transparentes para declaração contábil.
* **Early Adopters:** Engenheiros de software freelancers que valorizam APIs bem documentadas, previsibilidade e conciliação exata de saldos.

### 2. Propostas de Valor (Value Propositions)
* **Precisão Matemática Absoluta:** Eliminação total de erros de ponto flutuante no saldo através de cálculo atômico em centavos inteiros (`BIGINT`).
* **Livro-Razão Inviolável (*Double-Entry Ledger*):** Cada entrada no extrato é respaldada por uma contrapartida contábil simétrica (Débito = Crédito), impossibilitando "sumiço" de dinheiro.
* **Prevenção Nativa contra Falhas e Duplicações:** Suporte rigoroso a chaves de idempotência em todas as operações de escrita, protegendo o cliente contra cobranças duplicadas provocadas por perda de conexão móvel.
* **Auditoria e Linha do Tempo Imutável:** Histórico *append-only*, permitindo ao cliente rastrear cada mudança de status e transação de forma forense.

### 3. Canais (Channels)
* **Canais de Distribuição:**
  1. *Awareness (Descoberta):* Parcerias com contabilidades digitais e influenciadores de empreendedorismo PJ.
  2. *Evaluation (Avaliação):* Documentação interativa via Swagger/OpenAPI pública e sandbox funcional para simulação imediata.
  3. *Purchase (Adesão):* Onboarding digital simplificado com validação de CNPJ e dados cadastrais em segundos.
  4. *Delivery (Entrega):* Acesso imediato à conta e credenciais de API.
  5. *After Sales (Pós-Venda):* Notificações automáticas de liquidação e extrato contábil exportável para o contador.

### 4. Relacionamento com Clientes (Customer Relationships)
* **Self-Service Automatizado:** Interface intuitiva e respostas de API autodocumentadas e com catálogo de erros padronizado (`QIT000...` e `QIT001...`).
* **Transparência e Previsibilidade:** Qualquer falha de negócio devolve código específico e mensagem clara orientando a correção, em vez de mensagens genéricas.

### 5. Fontes de Receita (Revenue Streams)
* **Taxa por Operação:** Cobrança marginal por boleto ou liquidação financeira concluída com sucesso.
* **Spread sobre Float Financeiro:** Rendimento da custódia dos recursos mantidos em conta corrente regulamentada.
* **Serviços de Valor Agregado:** Relatórios fiscais pré-formatados para a Declaração Anual do MEI (DASN-SIMEI).

### 6. Recursos-Chave (Key Resources)
* **Tecnologia & Infraestrutura:** PostgreSQL com propriedades ACID plenas, API assíncrona FastAPI, SQLAlchemy ORM e conteinerização Docker.
* **Ativos Intelectuais:** Algoritmos de ordenação determinística de concorrência, motor de partidas dobradas e catálogo de erros semânticos.

### 7. Atividades-Chave (Key Activities)
* Manutenção da alta disponibilidade e latência P99 sub-100ms das rotas transacionais.
* Monitoramento de segurança, proteção contra invasão, IDOR e vazamento de identificadores sensíveis.
* Conciliação contábil diária garantindo que a soma global de todos os saldos bate com os lançamentos de ledger.

### 8. Parcerias-Chave (Key Partners)
* **Provedor de BaaS / Conectividade (QI Tech):** Infraestrutura regulatória, liquidação de boletos e acesso ao Sistema de Pagamentos Brasileiro (SPB).
* **Bureaus de Validação Cadastral:** Consulta instantânea de regularidade de CPF/CNPJ.
* **Plataformas de Gestão e ERPs:** Integrações diretas para automação do fluxo financeiro do cliente.

### 9. Estrutura de Custos (Cost Structure)
* **Custos Fixos:** Servidores de banco de dados relacional (RDS/PostgreSQL), instâncias de aplicação e ferramentas de monitoramento/log.
* **Custos Variáveis:** Tarifas por consulta a bureaus cadastrais e taxas de liquidação interbancária por transação.

---

## 4. Architectural Decision Records (ADRs - R7)

Registros formais de decisões técnicas fundamentadas no material de engenharia do Bootcamp QI Tech:

```
┌──────────┬──────────────────────────────────────────────────────────────────────────┬───────────┐
│ ADR ID   │ TÍTULO                                                                   │ STATUS    │
├──────────┼──────────────────────────────────────────────────────────────────────────┼───────────┤
│ ADR-001  │ Prevenção de Deadlock Concorrente via Ordenação Global de Locks          │ APROVADO  │
│ ADR-002  │ Representação Monetária em Centavos Inteiros (BIGINT) com 2 Casas         │ APROVADO  │
│ ADR-003  │ Arquitetura Contábil Imutável com Partidas Dobradas (Append-Only)         │ APROVADO  │
│ ADR-004  │ Desacoplamento de Chaves com UUID Público e Mitigação de IDOR             │ APROVADO  │
│ ADR-005  │ Idempotência Estrita e Catálogo Semântico de Erros (RFC 9457 / QIT)      │ APROVADO  │
│ ADR-006  │ Estados como Tabela de Domínio e Eventos Append-Only (Anti-ENUM)         │ APROVADO  │
└──────────┴──────────────────────────────────────────────────────────────────────────┴───────────┘
```

---

### ADR-001: Prevenção de Deadlock Concorrente via Ordenação Global de Locks (Dijkstra)

* **Status:** Aprovado.
* **Contexto:**
  Em transferências entre duas contas simultâneas (ex: Alice transferindo para Bob e Bob transferindo para Alice no mesmo milissegundo), duas threads disputam os locks de linha no PostgreSQL. Sem uma ordem pré-estabelecida:
  - Thread 1 tranca a Conta Alice e tenta trancar a Conta Bob.
  - Thread 2 tranca a Conta Bob e tenta trancar a Conta Alice.
  
  Isso produz a clássica condição de **Espera Circular (*Circular Wait*)**, gerando um **Deadlock**. O PostgreSQL detecta o ciclo após `deadlock_timeout` (1 segundo) e aborta uma das transações com o erro `DeadlockDetected (40P01)`. Se não for tratado, esse erro causa falha `HTTP 500` para o cliente final.

* **Alternativas Descartadas:**
  1. *Deixar o banco abortar e implementar Retentativas Automáticas (Retry com Backoff e Jitter):* Descartada por adicionar 40-60 linhas de código complexo, penalizar a latência com esperas de 1 segundo e arriscar novas falhas em cadeia sob pico de carga.
  2. *Lock Otimista (`version_id`):* Descartada porque em cenários com alta movimentação em contas centralizadoras, a taxa de rejeição e rollback é excessivamente alta.

* **Decisão:**
  Implementar a **Hierarquia Global de Recursos de Dijkstra (1965)**: sempre que uma transação exigir lock de mais de uma conta (`SELECT ... FOR UPDATE`), os IDs internos devem ser ordenados deterministicamente em ordem crescente antes da query:
  ```python
  ordered_ids = sorted([origin_id, destination_id])
  locked_accounts = repo.lock_accounts_for_update(ordered_ids)
  ```

* **Consequências:**
  - A espera circular torna-se matematicamente impossível: todas as threads adquirem recursos no mesmo sentido da fila.
  - Zero ocorrências de `DeadlockDetected (40P01)` no Postgres.
  - Custo de implementação trivial: 1 única linha de Python (`sorted(...)`), executada em nanossegundos.

---

### ADR-002: Representação Monetária em Centavos Inteiros (`BIGINT`) com 2 Casas Decimais

* **Status:** Aprovado.
* **Contexto:**
  Representar valores monetários com tipos de ponto flutuante IEEE 754 (`FLOAT`, `DOUBLE`) gera erros de conversão binária (ex: `0.1 + 0.2 = 0.30000000000000004` ou `165 * 1.40 = 230.99999999999997`). Em milhares de operações de débito e crédito, esses resíduos se acumulam, corrompendo balanços contábeis e gerando passivos regulatórios graves.

* **Alternativas Descartadas:**
  1. *Uso de `FLOAT` / `DOUBLE` no banco:* Proibição explícita (Restrição R6 do Bootcamp QI Tech).
  2. *Strings puras no banco:* Inviabiliza índices numéricos e validações nativas de integridade relacional (`CHECK >= 0`).

* **Decisão:**
  - **No Banco de Dados:** Todos os campos de saldo, taxas e transações são colunas `BIGINT` representando centavos inteiros (R$ 10,00 = `1000`; R$ 0,01 = `1`).
  - **Na Aplicação:** Aritmética exclusivamente de inteiros para operações de soma, subtração e checagem de saldo mínimo.
  - **Nos DTOs / Respostas da API:** A API expõe tanto o valor atômico inteiro (`balance_cents: 1000`) quanto a string decimal formatada com exatamente duas casas decimais (`balance: "10.00"`), garantindo consistência total para clientes web e mobile.

* **Consequências:**
  - Erros de arredondamento eliminados na origem.
  - Performance nativa máxima de operações inteiras de 64 bits.
  - Alinhamento total com as práticas do Stripe, Adyen e BACEN.

---

### ADR-003: Arquitetura Contábil Imutável com Partidas Dobradas (Append-Only)

* **Status:** Aprovado.
* **Contexto:**
  Sistemas financeiros tradicionais costumam alterar o saldo da conta diretamente com `UPDATE account SET balance = ...`. Isso destrói o histórico de como o saldo foi construído e inviabiliza auditorias contábeis. A exclusão lógica (*soft delete* com flag `is_deleted`) é um antipadrão que viola restrições de unicidade e esconde mutações destrutivas.

* **Decisão:**
  - Implementar o padrão canônico de **Partidas Dobradas (*Double-Entry Bookkeeping*)**: toda movimentação financeira gera no mínimo dois lançamentos na tabela imutável `ledger_entry` (um `DEBIT` e um `CREDIT` de mesmo valor).
  - Tabela `ledger_entry` é estritamente **Append-Only (R4)**: nenhuma linha recebe `UPDATE` ou `DELETE`.
  - O saldo na tabela `account` é mantido como uma visão materializada atualizada atomicamente na mesma transação para leitura de alta performance, assegurada por `CONSTRAINT check_positive_balance CHECK (balance_cents >= 0)`.
  - Estornos e correções não apagam o lançamento original: geram uma nova transação de estorno (*reversal*) com lançamentos inversos.

* **Consequências:**
  - Auditoria e conciliação contínua: a qualquer momento, o saldo de qualquer conta é verificável por $\sum(\text{Créditos}) - \sum(\text{Débitos})$.
  - Integridade forense garantida contra fraudes internas.

---

### ADR-004: Desacoplamento de Identificadores com UUID Público e Mitigação de IDOR

* **Status:** Aprovado.
* **Contexto:**
  Expor chaves primárias sequenciais do banco de dados (`id: 1, 2, 3...`) permite ataques de enumeração horizontal (*Insecure Direct Object Reference* - IDOR), nos quais um invasor descobre o volume de clientes da instituição ou tenta consultar transações alheias alterando o parâmetro da URL. Além disso, retornar `403 Forbidden` quando um recurso de terceiro é acessado confirma para o atacante que aquele recurso existe.

* **Decisão:**
  - **Separação de Chaves (R5):** O banco utiliza inteiros sequenciais (`SERIAL / INTEGER`) estritamente como chaves primárias e estrangeiras internas para máxima eficiência de índices e joins. Todas as entidades expõem externamente um UUIDv4 único (`party_key`, `account_key`, `transaction_key`).
  - **Mitigação de IDOR (R8):** Consultas a recursos que não pertencem ao usuário autenticado respondem uniformemente com `HTTP 404 Not Found` (em vez de `403 Forbidden`). O cliente não tem como distinguir entre um identificador inexistente e um identificador pertencente a outro cliente.

* **Consequências:**
  - Elimina riscos de enumeração de dados de clientes e espionagem de volume transacional.
  - Preserva performance de junções no PostgreSQL.

---

### ADR-005: Idempotência Estrita e Catálogo Semântico de Erros

* **Status:** Aprovado.
* **Contexto:**
  Redes móveis e conexões de internet são inerentemente não confiáveis. Quando um cliente envia um `POST /transactions` e a conexão cai antes de receber a resposta, o cliente tende a retentar. Sem idempotência, a conta sofrerá débito duplicado. Adicionalmente, retornar apenas status HTTP genéricos (como 400 seco) impede que sistemas automatizados tratem a falha programmaticamente.

* **Decisão:**
  - **Idempotência (R1/R2):** Todas as rotas de criação financeira exigem o cabeçalho HTTP `Idempotency-Key`. As requisições são registradas na tabela `transaction` com constraint `UNIQUE (idempotency_key)`. Requisições repetidas retornam exatamente o mesmo payload da transação original, sem executar novos débitos.
  - **Catálogo de Erros (R3):** Todo erro da aplicação retorna um corpo estruturado inspirado na RFC 9457 (Problem Details), com código único e imutável de negócio:
    - `QIT000...`: Erros de protocolo e infraestrutura (JSON inválido, ausência de token, rota não encontrada).
    - `QIT001...`: Erros de negócio da API (Saldo insuficiente, documento inválido, conta inativa, etc.).

* **Consequências:**
  - Eliminação de débitos acidentais provocados por retentativas de rede.
  - Integrações com clientes e parceiros tornam-se previsíveis e seguras.

---

### ADR-006: Estados como Tabela de Domínio e Histórico Append-Only (Anti-ENUM)

* **Status:** Aprovado.
* **Contexto:**
  Entidades financeiras essenciais (como Contas e Transações) possuem ciclo de vida rigoroso (ex: `PENDING`, `ACTIVE`, `BLOCKED`, `CLOSED` para Contas; `PENDING`, `SETTLED`, `FAILED`, `REVERSED` para Transações). A modelagem com tipos `ENUM` nativos do PostgreSQL (`CREATE TYPE status AS ENUM`) ou colunas de texto livre (`VARCHAR`) introduz fragilidades graves:
  - Modificar ou adicionar valores a um `ENUM` nativo em produção exige comandos DDL com trava de tabela (`EXCLUSIVE LOCK`), inviabiliza reversões simples e não permite associar metadados.
  - Strings livres (`VARCHAR`) não possuem integridade referencial nativa no banco, permitindo falhas de digitação e inconsistências que passam despercebidas.
  - Manter apenas uma coluna de status na entidade sobrescreve o estado anterior, destruindo a rastreabilidade temporal e a auditoria forense exigidas por órgãos reguladores (BACEN).

* **Alternativas Descartadas:**
  1. *Uso de ENUM nativo do PostgreSQL (`CREATE TYPE account_status AS ENUM`):* Descartada por travar tabelas em alterações de DDL, dificultar migrações zero-downtime e impedir extensão futura de metadados.
  2. *Coluna VARCHAR livre sem validação relacional:* Descartada por não garantir integridade no banco, deixando a consistência refém exclusivamente do código de aplicação.
  3. *Armazenar apenas o estado atual na entidade sem tabela de eventos:* Descartada porque sobrescrever o campo apaga a linha do tempo e impede a conciliação forense de auditoria.

* **Decisão:**
  - **Tabelas de Domínio para Status (`account_status`, `transaction_status`):** Estados vivem em tabelas próprias (`id SERIAL PRIMARY KEY`, `enumerator VARCHAR(50) UNIQUE NOT NULL`). A entidade armazena apenas `status_id INTEGER NOT NULL REFERENCES ..._status(id)`.
  - **Tabelas de Eventos de Status (`account_status_event`, `transaction_status_event`):** Cada transição de estado grava atomicamente uma linha em tabela de histórico estritamente **Append-Only** contendo `from_status_id`, `to_status_id`, `event_datetime` e `reason`.
  - **Máquina de Estados Centralizada no Controller:** O banco garante que o estado existe via chave estrangeira; o `Controller` aplica as regras de transição permitidas (ex: conta `CLOSED` ou transação `SETTLED` não sofrem novas mutações, respondendo com erro semântico `409 Conflict`).
  - **Desacoplamento nos DTOs:** A API interna utiliza IDs inteiros para joins de alta performance; os DTOs traduzem o valor para a string semântica na resposta JSON (`account.status.enumerator`).

* **Consequências:**
  - Integridade relacional garantida diretamente pelo PostgreSQL (sem risco de estados inválidos).
  - Adição de novos estados com simples `INSERT`, sem qualquer bloqueio de tabela (DDL).
  - Rastreabilidade forense total com linha do tempo de transições auditável.
  - Custo de uma junção a mais por leitura (mitigado por índices nas chaves e relacionamentos `lazy="selectin"` no ORM).

