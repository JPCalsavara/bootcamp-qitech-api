# Padrões de Projeto, Harness de Avaliação e Skills de Engenharia

Este documento extrai e formaliza todos os **padrões de projeto e regras arquiteturais** do repositório [`bootcamp-qitech-api`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api), estabelecendo como esses padrões alimentam um **Harness de Avaliação Contínua e Governança de Código** baseado no [**AI Quality Gatekeeper**](https://github.com/JPCalsavara/ai-gatekeeper) e em **Skills Modulares para Agentes Autônomos** inspiradas no modelo do [**mattpocock/skills**](https://github.com/mattpocock/skills).

---

## 1. Visão Geral da Arquitetura do Harness

O objetivo deste ecossistema é eliminar o "vibe coding" e a deriva arquitetural (*architectural drift*) em pull requests, garantindo que qualquer alteração realizada por desenvolvedores ou agentes de IA respeite as restrições rigorosas de um sistema financeiro de Core Banking.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FLUXO DE GOVERNANÇA E HARNESS                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘

   1. ALINHAMENTO & ESCRITA                 2. AI QUALITY GATEKEEPER CI/CD           3. RESULTADO
 (Skills estilo Matt Pocock)                 (LangGraph + Context Harness)

 ┌───────────────────────────┐             ┌───────────────────────────────┐      ┌───────────────┐
 │ /grill-financial-change   │             │ clean_diff                    │      │ PR Aprovado   │
 │   - Alinhamento de regras │             │   - Remove lockfiles e ruído  │      │ sem violação  │
 ├───────────────────────────┤             ├───────────────────────────────┤      └───────▲───────┘
 │ /model-state-machine      │             │ Context Harness               │              │
 │   - Tabela + Eventos + DTO│             │   - Embeddings L2 de diretriz │              │
 ├───────────────────────────┤ Git Commit  ├───────────────────────────────┤              │
 │ /enforce-layer-boundaries │────────────►│ LangGraph Multi-Tier:         │              │
 │   - Respeito às 10 pastas │   & Push    │  • Node 1: Test Failure Triage│              │
 ├───────────────────────────┤             │  • Node 2: Harness Review     ├──────────────┤
 │ /audit-concurrency-locks  │             │  • Node 3: Diff Sonar Triage  │              │
 │   - Dijkstra em FOR UPDATE│             │  • Node 4: Supervisor (Pro)   │      ┌───────┴───────┐
 └───────────────────────────┘             └───────────────┬───────────────┘      │ Patch Auto-   │
                                                           │                      │ Healing       │
                                                           └─────────────────────►│ (--apply-patch│
                                                                                  └───────────────┘
```

---

## 2. Catálogo de Padrões de Projeto Extraídos do Repositório

Abaixo estão os 10 padrões essenciais identificados no [`bootcamp-qitech-api`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api), com suas regras de verificação determinísticas para o Harness do Gatekeeper:

---

### Padrão 1: Arquitetura em Camadas com Fluxo Unidirecional Estrito

* **Problema:** Acoplamento entre protocolo HTTP, regras de negócio e consultas SQL, tornando o código difícil de testar e refatorar.
* **Implementação no Repositório:** A seta de chamada só avança em um sentido ([`docs/como-o-projeto-e-organizado.md#L258-L270`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/como-o-projeto-e-organizado.md#L258-L270)):
  $$\text{resources} \longrightarrow \text{controllers} \longrightarrow \text{repositories} \longrightarrow \text{models}$$
* **Regras do Gatekeeper (Context Harness):**
  1. `src/resources/` **NUNCA** pode importar de `repositories`, `models` ou executar queries SQL.
  2. `src/resources/` **NUNCA** pode ter comandos `raise` de regras de negócio (quem barra formato é o schema; quem decide regra é o controller).
  3. `src/repositories/` **NUNCA** pode tomar decisões de negócio (`if` de permissão/validação) ou importar controllers/resources.
  4. `src/models/` descreve apenas tabelas do SQLAlchemy sem métodos de regra.
* **Exemplo de Violação:**
  ```python
  # VIOLAÇÃO em src/resources/account.py
  @router.post("/accounts")
  def create_account(payload: dict, session: Session = Depends(get_db)):
      if session.query(Account).filter_by(document=payload["doc"]).first(): # ERRO: SQL no resource!
          raise HTTPException(409, "Duplicado") # ERRO: raise de regra no resource!
  ```
* **Forma Correta:**
  ```python
  # CORRETO em src/resources/account.py
  @router.post("/accounts")
  @SchemaHandler.validate("post_account.json")
  def create_account(payload: dict):
      controller = AccountController()
      return controller.create(payload), 201
  ```

---

### Padrão 2: Contrato de Entrada First via JSON Schema vs. DTO de Saída

* **Problema:** Misturar validação de payload com lógica de banco ou expor representações internas de banco (como IDs sequenciais ou colunas JSON cruas) diretamente na resposta HTTP.
* **Implementação no Repositório:**
  * **Entrada:** Validada via arquivo `.json` estático ([`src/schemas/`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/schemas/)) acionado pelo decorator [`@SchemaHandler.validate`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/utils/schema_handler.py) antes da primeira linha da rota rodar. Retorna `400 Bad Request` com código [`QIT000001`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/README.md#L656).
  * **Saída:** Formatada exclusivamente por Data Transfer Objects ([`src/dtos/`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/dtos/)), desacoplando colunas internas (`sample_entity_data`, `status_id`) em respostas planas e humanizadas ([`src/dtos/sample_entity_dto.py`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/dtos/sample_entity_dto.py)).
* **Regras do Gatekeeper:**
  1. Nenhuma rota pode receber corpo sem `@SchemaHandler.validate("<schema>.json")`.
  2. Nenhum model de banco pode ser serializado diretamente para JSON sem passar por um método estático de DTO (`DTO.obj_to_dict` ou `DTO.obj_to_simplified_dict`).
  3. Listagens devem usar DTO simplificado para evitar queries N+1 ao carregar históricos.

---

### Padrão 3: Gerenciamento de Sessão via Middleware e Contexto

* **Problema:** Sessões de banco vazando conexões, `commit`s disparados em camadas erradas ou health checks falhando por dependência desnecessária de banco.
* **Implementação no Repositório:**
  * O ciclo de vida nasce e morre no middleware ([`src/middlewares/session_manager.py`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/middlewares/session_manager.py)), mas a criação é *lazy* (rotas como `/health_check` e `/` não tocam no banco).
  * O controller obtém a sessão via [`BaseController`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/controllers/base_controller.py) chamando `get_context()`.
  * **Regra Absoluta:** O `self.session.commit()` ocorre **exclusivamente na última linha do Controller** antes do retorno. O Repository **NUNCA** faz commit.
* **Regras do Gatekeeper:**
  1. Bloquear qualquer `session.commit()` ou `session.rollback()` localizado fora de `src/controllers/` ou `src/middlewares/session_manager.py`.
  2. Bloquear chamadas a `get_context()` fora de `BaseController` ou middlewares.

---

### Padrão 4: Estados como Tabela de Domínio (Lookup Table) em vez de ENUM

* **Problema:** `ENUM` nativo do PostgreSQL (`CREATE TYPE ... AS ENUM`) causa bloqueios exclusivos de tabela em comandos DDL (`ALTER TYPE`), inviabilizando migrações zero-downtime. Colunas `VARCHAR` puras não garantem integridade relacional.
* **Implementação no Repositório:**
  * Tabela de domínio dedicada: `sample_entity_status` ([`database/database.sql#L1-L6`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/database/database.sql#L1-L6)).
  * A entidade armazena apenas `status_id INTEGER NOT NULL REFERENCES ..._status(id)`.
  * No Python, a classe de status herda de `Base` e define constantes com os valores das strings ([`src/models/sample_entity_status.py`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/models/sample_entity_status.py)).
  * No [`src/models/__init__.py`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/models/__init__.py), o status é importado **antes** da entidade principal para evitar falsos erros de importação circular.
* **Regras do Gatekeeper:**
  1. Rejeitar `ENUM` do PostgreSQL ou `Enum` do SQLAlchemy mapeado diretamente como tipo de coluna no banco.
  2. Toda coluna de estado deve ser `status_id INTEGER REFERENCES <entidade>_status(id)`.
  3. No DTO, o status exposto deve ser `entity.status.enumerator`.

---

### Padrão 5: Trilha de Auditoria Append-Only para Mudanças de Estado

* **Problema:** Colunas de status sofrem `UPDATE`, destruindo a resposta para "desde quando está bloqueada?" e "por que motivo?".
* **Implementação no Repositório:**
  * Toda entidade com estado possui uma tabela associada `_status_event` ([`database/database.sql#L30-L36`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/database/database.sql#L30-L36)).
  * Toda alteração de status no repositório atualiza a coluna `status_id` da entidade e simultaneamente cria uma nova linha na tabela de eventos ([`src/repositories/sample_entity_repository.py#L43-L51`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/repositories/sample_entity_repository.py#L43-L51)).
  * A tabela de eventos é estritamente **Append-Only** (zero `UPDATE` e zero `DELETE`).
* **Regras do Gatekeeper:**
  1. Qualquer método `update_status` no repository deve obrigatoriamente instanciar e salvar o respectivo `StatusEvent`.
  2. Nenhuma query de `UPDATE` ou `DELETE` pode ter como alvo tabelas que terminem com `_status_event`.

---

### Padrão 6: Máquina de Estados Centralizada no Controller

* **Problema:** Espalhar checagens de transição de estado pela API ou permitir mutações a partir de estados finais.
* **Implementação no Repositório:**
  * O banco valida se o estado existe (`FK`); o `Controller` valida se a transição é permitida ([`src/controllers/sample_entity_controller.py#L167-L172`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/controllers/sample_entity_controller.py#L167-L172)).
  * Estados finais (ex: `success`, `failed`, `closed`) rejeitam novas transições lançando erro semântico mapeado para `HTTP 409 Conflict` ([`QIT001002`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/README.md#L663)).
* **Regras do Gatekeeper:**
  1. Checagens de transição de estado devem residir em métodos privados do controller (ex: `_check_status_can_change`).
  2. Transições ilegais devem disparar exceção customizada mapeada no catálogo de erros com status HTTP 409 ou 422.

---

### Padrão 7: Prevenção de Deadlocks via Ordenação Global de Locks (Dijkstra)

* **Problema:** Duas transações simultâneas envolvendo os mesmos recursos em ordem inversa (Alice transfere para Bob e Bob transfere para Alice) geram espera circular (*Circular Wait*) e erro de deadlock (`40P01`) no PostgreSQL.
* **Implementação no Repositório:**
  * Aplicação da **Hierarquia Global de Recursos de Dijkstra (1965)** conforme [ADR-001](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/business-model-canvas-e-adrs.md#L126-L152):
  ```python
  ordered_ids = sorted([origin_id, destination_id])
  locked_accounts = repo.lock_accounts_for_update(ordered_ids)
  ```
* **Regras do Gatekeeper:**
  1. Sempre que uma query envolver `SELECT ... FOR UPDATE` com mais de um ID, a lista de IDs deve passar por `sorted(...)` antes da execução.
  2. Rejeitar padrões de retentativa automática (*retry loops*) que mascarem a falta de ordenação determinística de locks.

---

### Padrão 8: Representação Monetária em Centavos Inteiros (`BIGINT`)

* **Problema:** Uso de tipos `FLOAT` ou `DOUBLE` gera imprecisão de arredondamento binário IEEE 754 (ex: `0.1 + 0.2 = 0.30000000000000004`).
* **Implementação no Repositório:**
  * No banco: Colunas monetárias são `BIGINT` representando centavos inteiros (R$ 10,00 = `1000`).
  * Na aplicação: Aritmética puramente inteira.
  * Na saída (DTO): Exposição dupla: centavos inteiros (`balance_cents: 1000`) e string formatada com duas casas decimais (`balance: "10.00"`).
* **Regras do Gatekeeper:**
  1. Rejeitar tipos `Float`, `Double`, `REAL` em colunas monetárias no SQLAlchemy ou SQL.
  2. Impedir divisões com `/` em regras financeiras; exigir divisões inteiras `//` com tratamento de resto/centavos residuais.

---

### Padrão 9: Desacoplamento de Chaves (UUID Público vs. ID Sequencial) e Mitigação de IDOR

* **Problema:** Expor chaves primárias sequenciais (`id: 1, 2, 3`) permite ataques de enumeração horizontal (IDOR). Retornar `403 Forbidden` quando um recurso de terceiro é acessado confirma para o atacante que o recurso existe.
* **Implementação no Repositório:**
  * O banco usa `SERIAL / INTEGER` internamente para joins e chaves estrangeiras de alta performance.
  * A API externa usa exclusivamente `UUIDv4` (`sample_entity_key`, `account_key`, `party_key`).
  * Consultas a recursos inexistentes ou não pertencentes ao usuário respondem uniformemente com `HTTP 404 Not Found` ([ADR-004](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/docs/business-model-canvas-e-adrs.md#L194-L208)).
* **Regras do Gatekeeper:**
  1. URLs e schemas externos não podem expor parâmetros como `id: int`. Apenas chaves públicas `*_key: str`.
  2. Em falhas de propriedade de recurso, responder sempre `404` (nunca `403`).

---

### Padrão 10: Idempotência Estrita e Catálogo Semântico de Erros (RFC 9457 / QIT)

* **Problema:** Retentativas de requisição em conexões instáveis provocam cobranças ou criações duplicadas. Erros sem código semântico impedem tratamento programático por clientes.
* **Implementação no Repositório:**
  * Criações financeiras exigem o cabeçalho `Idempotency-Key` e possuem restrição `UNIQUE (idempotency_key)` na tabela.
  * Catálogo de Erros estruturado ([`src/errors/`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/errors/)):
    * `QIT000...`: Erros de protocolo/infraestrutura (ex: `QIT000001` Payload inválido, `QIT000002` Token ausente).
    * `QIT001...`: Erros de negócio específicos da aplicação.
    * Validação em tempo de inicialização ([`error_verification`](file:///home/jpcalsavara/projetos/andamento/bootcamp-qitech-api/src/errors/base_error.py)): a aplicação não sobe se houver códigos duplicados.
* **Regras do Gatekeeper:**
  1. Qualquer novo erro criado em `src/errors/custom_errors.py` deve conter classe própria herdando de `BaseError`, com `title`, `description`, `translation`, `http_code` e código `QIT001...` sequencial não repetido.
  2. Rotas de mutação financeira devem exigir e validar unicidade de `Idempotency-Key`.

---

## 3. Integração com o AI Quality Gatekeeper

O repositório [`JPCalsavara/ai-gatekeeper`](https://github.com/JPCalsavara/ai-gatekeeper) utiliza LangGraph com Dynamic Model Tiering e um **Context Harness** com busca vetorial local pré-normalizada (L2 unit length).

### A. Estrutura do `docs/guidelines.md` no Gatekeeper

O arquivo de diretrizes do Gatekeeper deve ser alimentado diretamente com os padrões extraídos deste documento:

```markdown
# Engineering Guidelines - Bootcamp QI Tech API

## Architecture & Layers
- [ARCH-001] Resources must not import repositories, models, or execute SQL queries.
- [ARCH-002] Business rules and validations belong exclusively to Controllers.
- [ARCH-003] Database commits (session.commit()) are permitted only in Controllers as the final operation.

## State Management & Immutability
- [STATE-001] States must be modeled as lookup tables (*_status) with integer foreign keys, never as native ENUMs or raw VARCHARs.
- [STATE-002] Every state mutation must append an immutable entry to the corresponding *_status_event table.
- [STATE-003] Final states (success, failed, closed) cannot transition to any other state and must reject updates with HTTP 409 (QIT001002).

## Concurrency & Financial Rigor
- [FIN-001] Multi-account transactions must sort account IDs (Dijkstra lock ordering) before acquiring SELECT ... FOR UPDATE.
- [FIN-002] All monetary values must be stored as BIGINT cents. FLOAT/DOUBLE are strictly forbidden.
- [FIN-003] Financial transfers must enforce double-entry ledger bookkeeping (DEBIT + CREDIT) in an append-only ledger_entry table.
- [FIN-004] Mutation endpoints must enforce idempotency via Idempotency-Key header.
```

### B. Indexação Vetorial Pré-Normalizada (`context_harness.py`)

No pipeline do Gatekeeper:
1. `context_harness.py` converte `docs/guidelines.md` em chunks temáticos.
2. Gera embeddings e aplica normalização $L_2$ ($v' = \frac{v}{\|v\|_2}$).
3. Salva em `context_harness.json`.
4. Durante a análise do diff do PR, o **Node 2 (Flash Tier - Code Review)** realiza busca por produto escalar ultrarrápido ($O(1)$ de normalização em tempo de query) para encontrar quais regras foram potencialmente violadas pelas linhas alteradas.

### C. Pipeline LangGraph com Auto-Cura

```
[PR Diff] ──► clean_diff ──► Node 2: Context Harness Review (Flash) ──┐
                                                                     ├──► Node 4: Supervisor (Pro) ──► Unified Patch (--apply-patch)
[Tests]   ──► tests.log  ──► Node 1: Test Failure Triage (Flash)   ──┤
```

Quando o Gatekeeper identifica uma violação (ex: um `float` em coluna financeira ou um `session.commit()` no repository):
* O **Node 4 (Supervisor)** sintetiza a justificativa com referência direta ao código de diretriz (ex: `[FIN-002]`).
* Gera um bloco `diff -u` com a correção exata.
* Se invocado com `--apply-patch`, o script aplica a correção com `git apply --check` automaticamente.

---

## 4. Skills para Agentes de Engenharia (Inspiradas em `mattpocock/skills`)

Seguindo o design de skills modulares, composáveis e focadas em prevenir falhas clássicas de agentes de IA ([`mattpocock/skills`](https://github.com/mattpocock/skills)), definimos o catálogo de skills para o desenvolvimento neste repositório:

---

### Skill 1: `/grill-financial-change`
* **Gatilho:** Invocada antes de implementar qualquer funcionalidade que envolva dinheiro, saldo, transferência ou transação.
* **Propósito:** Prevenir o clássico problema *"The Agent Didn't Do What I Want"* através de um alinhamento detalhado e interrogatório técnico.
* **Comportamento do Agente:**
  1. Perguntar: *"Quais contas participam da operação? Qual é o sentido do fluxo de fundos?"*
  2. Perguntar: *"Como a idempotência será tratada em caso de timeout de rede?"*
  3. Perguntar: *"Qual a estratégia de locking para evitar deadlocks caso ocorra concorrência reversa?"*
  4. Exigir confirmação de que os valores serão estritamente em centavos inteiros (`BIGINT`).
  5. Não escrever nenhuma linha de código até que todas as respostas estejam claras.

---

### Skill 2: `/enforce-layer-boundaries`
* **Gatilho:** Invocada ao criar ou modificar rotas, controllers ou repositórios.
* **Propósito:** Garantir a disciplina das 10 pastas e o sentido único da dependência.
* **Comportamento do Agente:**
  1. Verificar se novos arquivos foram exportados no `__init__.py` da pasta correspondente.
  2. Verificar se a ordem em `src/models/__init__.py` respeita a precedência de dependência (status antes da entidade).
  3. Conferir se nenhum `raise` de negócio está em `src/resources/`.
  4. Conferir se nenhum SQL ou query do SQLAlchemy está fora de `src/repositories/`.
  5. Assegurar que `self.session.commit()` está somente no final do controller.

---

### Skill 3: `/model-state-machine`
* **Gatilho:** Invocada ao criar uma nova entidade que possua ciclo de vida ou estados.
* **Propósito:** Implementar o padrão canônico de tabela de domínio + tabela de eventos + regras de transição.
* **Comportamento do Agente:**
  1. Criar a tabela `<entidade>_status` com `id SERIAL PK` e `enumerator VARCHAR(50) UK`.
  2. Criar a tabela `<entidade>_status_event` com campos `from_status_id`, `to_status_id`, `event_datetime` e `reason`.
  3. Criar os models correspondentes em `src/models/`.
  4. Adicionar a máquina de estados no controller com validação de estados finais e emissão de erro `HTTP 409` com código `QIT001...`.
  5. Mapear o status textual no DTO de saída.

---

### Skill 4: `/audit-concurrency-locks`
* **Gatilho:** Invocada em revisões de código de métodos transacionais concorrentes.
* **Propósito:** Garantir ausência matemática de deadlocks em operações com múltiplos registros.
* **Comportamento do Agente:**
  1. Localizar todas as chamadas a `with_for_update()` ou `SELECT ... FOR UPDATE`.
  2. Verificar se os identificadores dos recursos foram ordenados deterministicamente com `sorted(...)` antes da aquisição.
  3. Confirmar que a transação possui timeout configurado e não realiza chamadas HTTP externas com lock adquirido.

---

### Skill 5: `/verify-idempotency-and-ledger`
* **Gatilho:** Invocada ao implementar endpoints de mutação financeira (`POST /transactions`, estornos, liquidações).
* **Propósito:** Garantir partidas dobradas invioláveis e prevenção contra retentativas duplicadas.
* **Comportamento do Agente:**
  1. Exigir o cabeçalho `Idempotency-Key` no schema de entrada.
  2. Garantir que a tabela possui constraint `UNIQUE(idempotency_key)`.
  3. Verificar se toda transferência gera no mínimo dois lançamentos na tabela `ledger_entry` (um `DEBIT` e um `CREDIT` com valor idêntico).
  4. Garantir que a soma de todos os débitos e créditos do ledger concilia perfeitamente com o saldo materializado da conta.

---

## 5. Guia de Aplicação Prática no Repositório

Para ativar essa infraestrutura no dia a dia:

1. **Geração do Índice de Diretrizes:**
   ```bash
   python /caminho/para/ai-gatekeeper/context_harness.py \
     --guidelines docs/padroes-projeto-harness-gatekeeper-skills.md \
     --output context_harness.json
   ```
2. **Execução Local do Gatekeeper em PRs:**
   ```bash
   python /caminho/para/ai-gatekeeper/gatekeeper.py \
     --diff git.diff \
     --tests pytest.log \
     --harness context_harness.json \
     --apply-patch
   ```
3. **Uso das Skills nos Agentes de Codificação:**
   * Configure os prompts de sistema ou comandos de barra (`/grill-financial-change`, `/model-state-machine`) no ambiente de desenvolvimento do time (Antigravity, Claude Code, Cursor ou Copilot), apontando para as diretrizes deste documento.
