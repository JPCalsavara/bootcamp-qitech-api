# CoreBank MEI: Business Model Canvas & ADRs de Arquitetura

Este documento consolida a modelagem estratégica de negócio baseada na metodologia oficial do **Business Model Canvas** (Alexander Osterwalder & Yves Pigneur) e o registro das decisões arquiteturais fundamentais (**ADRs**) para o desenvolvimento da API de Core Banking voltada para MEIs e profissionais autônomos.

---

## 1. Visão Geral do Projeto

* **Nome do Produto:** CoreBank MEI
* **Categoria:** API de Core Banking & Ledger Contábil em Tempo Real
* **Público Principal:** Microempreendedores Individuais (MEIs) e Prestadores de Serviços Autônomos (PJ)
* **Objetivo Central:** Oferecer uma infraestrutura de conta de pagamento simples, ágil e matematicamente precisa, com **onboarding unificado que já provisiona as duas contas vinculadas (Conta PJ com CNPJ e Conta PF com CPF)**, eliminando desvios contábeis, confusão patrimonial e riscos de cobranças duplicadas ou inconsistências transacionais.

---

## 2. Business Model Canvas (Poster Oficial)

Baseado nos 9 blocos conceituais do framework do Business Model Canvas:

```
┌─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┐
│ 8. PARCERIAS-CHAVE              │ 7. ATIVIDADES-CHAVE             │ 2. PROPOSTAS DE VALOR           │ 4. RELACIONAMENTO COM CLIENTES  │ 1. SEGMENTOS DE CLIENTES        │
│ (Key Partners)                  │ (Key Activities)                │ (Value Propositions)            │ (Customer Relationships)        │ (Customer Segments)             │
│                                 │                                 │                                 │                                 │                                 │
│ • Provedores de BaaS (QI Tech)  │ • Desenvolvimento e evolução da │ • Separação Patrimonial Nativa: │ • Suporte Digital Automatizado: │ • Microempreendedores           │
│   para conectividade ao SPB/PIX.│   API de Core Banking e Ledger. │   Onboarding único cria Conta PJ│   Self-service via portal web/  │   Individuais (MEIs) do setor   │
│ • Softwares de Gestão Financeira│ • Gestão de conciliação bancária│   (CNPJ) e Conta PF (CPF)       │   aplicativo.                   │   de serviços e comércio local. │
│   e ERPs (ex: ContaAzul, Bling).│   e integridade contábil.       │   vinculadas ao Customer.       │ • Transparência Absoluta:       │ • Profissionais PJ Autônomos:   │
│ • Emissores de Certificados e   │ • Monitoramento de segurança,   │ • Conciliação Contábil em Tempo │   notificação clara de eventos  │   desenvolvedores, designers,   │
│   Bureaus de Crédito/KYC.       │   mitigação de fraudes e locks. │   Real: zero centavo perdido    │   financeiros e extrato com     │   consultores, redatores.       │
│ • Contabilidades online parceiras│• Compliance com normas de      │   com motor de partidas dobradas│   dados de contraparte e saldo. │                                 │
│   para indicação mútua.         │   Instituição de Pagamento (IP) │ • 100% Isenção de IRPF:         │ • Comunidades & Desenvolvedores:│ Early Adopters:                 │
│                                 │   e Resoluções do BACEN (MED).  │   Ledger formal comprova lucro  │   documentação Swagger/OpenAPI  │ • Freelancers tech e consultores│
│                                 ├─────────────────────────────────┤   isento (Art. 14 da LC 123/06).│   aberta e sandbox de testes.   │   de tecnologia.                │
│                                 │ 6. RECURSOS-CHAVE               │ • Segurança Transacional Forte: │                                 │                                 │
│                                 │ (Key Resources)                 │   PIN de 4 dígitos separado do  │                                 │                                 │
│                                 │                                 │   login e prevenção de deadlock ├─────────────────────────────────┤                                 │
│                                 │ • Motor de Ledger Imutável em   │   via ordenação de Dijkstra.    │ 3. CANAIS                       │                                 │
│                                 │   PostgreSQL com locking seguro.│ • Resiliência com Idempotência: │ (Channels)                      │                                 │
│                                 │ • Stack robusta: Python/FastAPI,│   tabela dedicada com TTL 24h   │                                 │                                 │
│                                 │   SQLAlchemy 2.0 e Docker.      │   contra falhas de rede.        │ • API REST Direta (B2B/B2B2C).  │                                 │
│                                 │ • Equipe de engenharia focada   │                                 │ • Parcerias de integração com   │                                 │
│                                 │   em sistemas distribuídos/ACID.│ Conceito de Alto Nível:         │   ERPs e emissores de NF-e.     │                                 │
│                                 │ • Licença e credenciais de BaaS.│ "A infraestrutura financeira da │ • Aplicativo Mobile / Web leve. │                                 │
│                                 │                                 │ Stripe com o rigor contábil de  │                                 │                                 │
│                                 │                                 │ um core banking para o MEI."    │                                 │                                 │
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
* **Separação Patrimonial com Onboarding Unificado:** Em um único cadastro (`POST /customers`), o empreendedor cria sua titularidade e ganha simultaneamente sua **Conta PJ** (para operar o negócio) e sua **Conta PF** (para despesas pessoais), sem burocracias separadas.
* **Precisão Matemática Absoluta:** Eliminação total de erros de ponto flutuante no saldo através de cálculo atômico em centavos inteiros (`BIGINT`).
* **Livro-Razão Inviolável (*Double-Entry Ledger*):** Cada entrada no extrato é respaldada por uma contrapartida contábil simétrica (Débito = Crédito), impossibilitando "sumiço" de dinheiro.
* **Comprovação Fiscal de 100% de Isenção de IRPF (Art. 14 da LC 123/2006):** O extrato do ledger formaliza a transferência PJ $\rightarrow$ PF como `PROFIT_DISTRIBUTION`, permitindo isenção total de imposto de renda da pessoa física sobre o lucro real apurado.
* **Prevenção Nativa contra Falhas e Duplicações:** Suporte rigoroso a chaves de idempotência em tabela dedicada com TTL de 24 horas, protegendo o cliente contra cobranças duplicadas provocadas por perda de conexão móvel.
* **Auditoria e Linha do Tempo Imutável:** Histórico *append-only*, permitindo ao cliente rastrear cada mudança de status e transação de forma forense.

### 3. Canais (Channels)
* **Canais de Distribuição:**
  1. *Awareness (Descoberta):* Parcerias com contabilidades digitais e influenciadores de empreendedorismo PJ.
  2. *Evaluation (Avaliação):* Documentação interativa via Swagger/OpenAPI pública e sandbox funcional para simulação imediata.
  3. *Purchase (Adesão):* Onboarding digital simplificado com validação de CPF, CNPJ e criação das contas em segundos.
  4. *Delivery (Entrega):* Acesso imediato à conta e credenciais de API.
  5. *After Sales (Pós-Venda):* Notificações automáticas de liquidação e extrato contábil exportável para o contador.

### 4. Relacionamento com Clientes (Customer Relationships)
* **Self-Service Automatizado:** Interface intuitiva e respostas de API autodocumentadas e com catálogo de erros padronizado (`QIT000...` e `QIT001...`).
* **Transparência e Previsibilidade:** Qualquer falha de negócio devolve código específico e mensagem clara orientando a correção, em vez de mensagens genéricas.

### 5. Fontes de Receita (Revenue Streams)
* **Taxa Transacional de Liquidação:** Cobrança atômica sobre recebimentos comerciais (PIX R$ 0,90 e Boleto R$ 2,50 por liquidação concluída, com débito no ledger conforme ADR-0008).
* **MDR de Link de Pagamento (Cartão):** Taxa percentual sobre vendas no cartão de crédito à vista (2,99%) e parcelado (3,99%).
* **Spread de Antecipação de Recebíveis:** Desconto pró-rata de 1,99% a 2,49% a.m. para antecipação imediata de vendas a prazo.
* **Spread e Juros de Capital de Giro (CCB):** Juros remuneratórios de 2,89% a 4,50% a.m. em empréstimos parcelados com trava dinâmica de recebíveis via QI Tech SCD.
* **Interchange Fee de Cartão PJ Débito:** Receita de 0,80% a 1,20% paga pelas adquirentes/bandeira sobre transações no cartão de débito corporativo.
* **Float de Tesouraria:** Captura de rendimento de liquidez sobre saldos mantidos em custódia na `SettlementAccount` e depósitos livres de curto prazo (< 30 dias).
* **Serviços de Valor Agregado:** Relatórios fiscais pré-formatados para a Declaração Anual do MEI (DASN-SIMEI) e DRE gerencial.

### 6. Recursos-Chave (Key Resources)
* **Tecnologia & Infraestrutura:** PostgreSQL com propriedades ACID plenas, API assíncrona FastAPI, SQLAlchemy ORM e conteinerização Docker.
* **Ativos Intelectuais:** Algoritmos de ordenação determinística de concorrência (Dijkstra), motor de partidas dobradas, tabela dedicada de idempotência e catálogo de erros semânticos.

### 7. Atividades-Chave (Key Activities)
* Manutenção da alta disponibilidade e latência P99 sub-100ms das rotas transacionais.
* Monitoramento de segurança, proteção contra invasão, IDOR e vazamento de identificadores sensíveis.
* Conciliação contábil diária garantindo que a soma global de todos os saldos bate com os lançamentos de ledger.

### 8. Parcerias-Chave (Key Partners)
* **Provedor de BaaS e SCD (QI Tech):** Infraestrutura regulatória, conectividade ao SPB/PIX, emissão de CCBs digitais e custódia de CDB/RDB de liquidez diária.
* **Bureaus de Validação Cadastral e Antifraude (Serasa/Datavalid/DICT):** Consulta instantânea de regularidade de CPF/CNPJ, verificação de titulares do MEI e prevenção ao MED.
* **Plataformas de Gestão e ERPs (Bling, ContaAzul):** Integrações diretas via API para automação do fluxo financeiro e conciliação do MEI.

### 9. Estrutura de Custos (Cost Structure)
* **Custos Fixos:** Servidores de banco de dados relacional (RDS/PostgreSQL), instâncias de aplicação e ferramentas de monitoramento/log.
* **Custos Variáveis:** Tarifas por consulta a bureaus cadastrais, taxas de liquidação interbancária por transação e custo de funding/risco de crédito.

---

## 4. Architectural Decision Records (ADRs)

Registros formais de decisões técnicas fundamentadas no material de engenharia do Bootcamp QI Tech e alinhadas ao diretório `docs/adr/`:

```
┌──────────┬──────────────────────────────────────────────────────────────────────────┬───────────┐
│ ADR ID   │ TÍTULO                                                                   │ STATUS    │
├──────────┼──────────────────────────────────────────────────────────────────────────┼───────────┤
│ ADR-0001 │ Adoção Exclusiva de Testes de Integração na Borda HTTP (Sem Mocks Unit)  │ APROVADO  │
│ ADR-0002 │ Prevenção de Deadlock Concorrente via Ordenação Global de Locks (Dijkstra│ APROVADO  │
│ ADR-0003 │ Representação Monetária em Centavos Inteiros (BIGINT) com 2 Casas         │ APROVADO  │
│ ADR-0004 │ Arquitetura Contábil Imutável com Partidas Dobradas (Append-Only)         │ APROVADO  │
│ ADR-0005 │ Desacoplamento de Identificadores com UUID Público (customer_key, etc.)  │ APROVADO  │
│ ADR-0006 │ Idempotência Estrita em Tabela Dedicada e Catálogo Semântico de Erros    │ APROVADO  │
│ ADR-0007 │ Estados como Tabela de Domínio e Histórico Append-Only (Anti-ENUM)         │ APROVADO  │
│ ADR-0008 │ Tarifação Transacional com Débito Atômico no Ledger (Gross + Fee Debit)   │ APROVADO  │
└──────────┴──────────────────────────────────────────────────────────────────────────┴───────────┘
```

> [!TIP]
> Para o índice executivo completo, mapa Mermaid de interdependência arquitetural e matriz de impacto no código, consulte [docs/adr/README.md](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/README.md).

---

### ADR-0001: Adoção Exclusiva de Testes de Integração na Borda HTTP (Sem Mocks Unitários)
*Consulte o arquivo individual completo em [docs/adr/0001-apenas-testes-de-integracao.md](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0001-apenas-testes-de-integracao.md).*

* **Status:** Aprovado.
* **Decisão:** Adotar como padrão obrigatório para o projeto **apenas testes de integração**, dispensando testes unitários isolados com mocks. Todo teste deve exercitar o fluxo ponta a ponta através das rotas da API (usando `TestClient` / `ClientRequisition`) contra o banco de dados PostgreSQL local real.

---

### ADR-0002: Prevenção de Deadlock Concorrente via Ordenação Global de Locks (Dijkstra)
*Consulte o arquivo individual completo em [docs/adr/0002-prevencao-deadlock-ordenacao-dijkstra.md](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0002-prevencao-deadlock-ordenacao-dijkstra.md).*

* **Status:** Aprovado.
* **Decisão:** Implementar a **Hierarquia Global de Recursos de Dijkstra (1965)**: sempre que uma transação exigir lock de mais de uma conta (`SELECT ... FOR UPDATE`), os IDs internos numéricos devem ser ordenados deterministicamente em ordem crescente antes da query: `sorted([origin_id, destination_id])`. Elimina qualquer ocorrência de erro `DeadlockDetected (40P01)`.

---

### ADR-0003: Representação Monetária em Centavos Inteiros (`BIGINT`) com 2 Casas Decimais
*Consulte o arquivo individual completo em [docs/adr/0003-representacao-monetaria-centavos-bigint.md](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0003-representacao-monetaria-centavos-bigint.md).*

* **Status:** Aprovado.
* **Decisão:** Todos os campos monetários no banco são colunas `BIGINT` representando centavos inteiros (R$ 10,00 = `1000`). Aritmética exclusivamente de inteiros na aplicação. Respostas da API expõem tanto `balance_cents` (inteiro) quanto `balance` (string formatada com duas casas decimais). Elimina resíduos de ponto flutuante IEEE 754.

---

### ADR-0004: Arquitetura Contábil Imutável com Partidas Dobradas (Append-Only)
*Consulte o arquivo individual completo em [docs/adr/0004-arquitetura-contabil-partidas-dobradas.md](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0004-arquitetura-contabil-partidas-dobradas.md).*

* **Status:** Aprovado.
* **Decisão:** Toda movimentação gera no mínimo dois lançamentos na tabela imutável `ledger_entry` (um `DEBIT` e um `CREDIT` de mesmo valor). A tabela `ledger_entry` é estritamente **Append-Only**. Saldo em `account` atua como cache materializado protegido por `CHECK (balance_cents >= 0)`. Estornos geram novas transações de estorno com lançamentos inversos.

---

### ADR-0005: Desacoplamento de Identificadores com UUID Público e Mitigação de IDOR
*Consulte o arquivo individual completo em [docs/adr/0005-desacoplamento-identificadores-uuid-publico.md](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0005-desacoplamento-identificadores-uuid-publico.md).*

* **Status:** Aprovado.
* **Decisão:** O banco utiliza inteiros sequenciais (`SERIAL / INTEGER`) estritamente como chaves primárias e estrangeiras internas para máxima eficiência de índices e joins. Todas as entidades expõem externamente um UUIDv4 único (`customer_key`, `account_key`, `transaction_key`). Consultas a recursos que não pertencem ao usuário autenticado respondem uniformemente com `HTTP 404 Not Found` para mitigar ataques IDOR.

---

### ADR-0006: Idempotência Estrita em Tabela Dedicada e Catálogo Semântico de Erros
*Consulte o arquivo individual completo em [docs/adr/0006-idempotencia-tabela-dedicada-catalogo-erros.md](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0006-idempotencia-tabela-dedicada-catalogo-erros.md).*

* **Status:** Aprovado.
* **Decisão:** Requisições financeiras utilizam o cabeçalho `Idempotency-Key` e são registradas na tabela desacoplada `idempotency_record` com TTL de 24 horas. Respostas de sucesso ou falha de validação são cacheadas, evitando reprocessamentos acidentais. Erros seguem o catálogo semântico estruturado (`QIT000...` e `QIT001...`).

---

### ADR-0007: Estados como Tabela de Domínio e Histórico Append-Only (Anti-ENUM)
*Consulte o arquivo individual completo em [docs/adr/0007-estados-tabela-dominio-historico-append-only.md](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0007-estados-tabela-dominio-historico-append-only.md).*

* **Status:** Aprovado.
* **Decisão:** Estados de contas e transações residem em tabelas de domínio (`account_status`, `transaction_status`). Mutações de estado gravam eventos na tabela de histórico append-only (`account_status_event`, `transaction_status_event`). A máquina de estados é governada centralizadamente no `Controller` com lock pessimista (`SELECT FOR UPDATE`).

---

### ADR-0008: Tarifação Transacional com Débito Atômico no Ledger (Gross + Fee Debit)
*Consulte o arquivo individual completo em [docs/adr/0008-tarifacao-transacional-debito-atomico-ledger.md](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/adr/0008-tarifacao-transacional-debito-atomico-ledger.md).*

* **Status:** Aprovado.
* **Decisão:** Toda cobrança liquidada é creditada pelo valor bruto total na `BusinessAccount` e, no mesmo milissegundo em transação atômica do PostgreSQL com lock ordenado de Dijkstra, a tarifa da plataforma é debitada para a conta contábil de receita (`FeeRevenueAccount`). Garante que o extrato espelhe 1:1 a Nota Fiscal (NFS-e) do MEI e viabilize a comprovação fiscal do teto de R$ 81k.

---

## 5. Mapeamento da Suíte de RFCs Oficiais

A arquitetura do CoreBank MEI está formalizada em 4 RFCs consolidadas por domínio arquitetural em `docs/rfc/` (com histórico preservado em `docs/rfc/archive/`):

1. [**RFC 01 — Onboarding Seguro, Identidade MEI e Provisionamento de Contas Vinculadas (PF/PJ)**](rfc/rfc-01-onboarding-identidade-contas.md): Modelo de titularidade unificada, esteira assíncrona de KYC/Antifraude (Receita Federal, DICT/MED, Bureau Serasa), máquina de estados auditável do `Customer`, contas vinculadas (`BUSINESS` e `PERSONAL`), credenciais Argon2id (senha e PIN) e controle de saldo cautelar.
2. [**RFC 02 — Motor Financeiro, Ledger de Partidas Dobradas, Meios de Pagamento e Liquidação Transacional**](rfc/rfc-02-ledger-meios-pagamento-liquidacao.md): Motor contábil imutável de partidas dobradas, ordenação determinística de Dijkstra contra deadlocks, idempotência com tabela dedicada (TTL 24h), cobranças multimodais (PIX QR dinâmico, Boleto Híbrido, Link de Cartão), webhooks e débito atômico de tarifas transacionais.
3. [**RFC 03 — Governança Patrimonial, Envelopes Financeiros (Pockets) e Tesouraria Remunerada (CDB/RDB)**](rfc/rfc-03-governanca-caixa-envelopes-tesouraria.md): Separação patrimonial via teto de pró-labore (`TransferPolicy`), envelopes de retenção tributária e reservas (`Pocket`), rastreador em tempo real do teto de faturamento fiscal de R$ 81k (`RevenueTracker`), e tesouraria remunerada (100% CDI) com *Cash Sweep* invisível no débito.
4. [**RFC 04 — Linhas de Crédito MEI, Cédula de Crédito Bancário (CCB) e Antecipação com Trava Dinâmica**](rfc/rfc-04-linhas-credito-trava-recebiveis.md): Antecipação de recebíveis de vendas futuras, Cédula de Crédito Bancário (CCB) de Capital de Giro via QI Tech SCD, trava dinâmica de recebíveis com retenção automática em `Pocket` de amortização e garantia patrimonial cruzada PF/PJ.
