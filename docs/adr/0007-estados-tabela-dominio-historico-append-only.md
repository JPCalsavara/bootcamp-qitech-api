# ADR-0007: Estados como Tabela de Domínio e Histórico Append-Only (Anti-ENUM)

| | |
|---|---|
| **Status** | **Aprovado** |
| **Data** | 19/09/2026 |
| **Decisores** | João Pedro Calsavara / Engenharia Core Banking |
| **Tags** | `maquina-de-estados`, `anti-enum`, `tabela-dominio`, `auditoria` |

---

## Contexto
Entidades financeiras essenciais (como Contas e Transações) possuem ciclo de vida rigoroso (`created`, `active`, `blocked`, `closed` para Contas; `pending`, `settled`, `failed`, `reversed` para Transações). A modelagem com tipos `ENUM` nativos do PostgreSQL (`CREATE TYPE status AS ENUM`) ou colunas de texto livre (`VARCHAR`) introduz fragilidades graves:
- Modificar ou adicionar valores a um `ENUM` nativo em produção exige comandos DDL com trava de tabela (`EXCLUSIVE LOCK`), inviabiliza reversões simples e impede acoplamento de metadados.
- Strings livres (`VARCHAR`) não possuem integridade referencial nativa no banco, permitindo falhas de digitação e inconsistências que passam despercebidas.
- Manter apenas uma coluna de status na entidade sobrescreve o estado anterior, destruindo a rastreabilidade temporal e a auditoria forense exigidas por órgãos reguladores (BACEN).

## Decisão
1. **Tabelas de Domínio para Status (`account_status`, `transaction_status`):** Estados vivem em tabelas próprias (`id SERIAL PRIMARY KEY`, `enumerator VARCHAR(50) UNIQUE NOT NULL`). A entidade armazena apenas `status_id INTEGER NOT NULL REFERENCES ..._status(id)`.
2. **Tabelas de Eventos de Status (`account_status_event`, `transaction_status_event`):** Cada transição de estado grava atomicamente uma linha em tabela de histórico estritamente **Append-Only** contendo `from_status_id`, `to_status_id`, `reason_code`, `reason` e `event_datetime`.
3. **Máquina de Estados Centralizada no Controller:** O banco garante que o estado existe via chave estrangeira; o `Controller` aplica as regras de transição permitidas (ex: conta `closed` não sofre novas mutações, respondendo com erro semântico `409 Conflict`).
4. **Desacoplamento nos DTOs:** A API interna utiliza IDs inteiros para joins de alta performance; os DTOs traduzem o valor para a string semântica na resposta JSON (`account.status.enumerator`).

## Consequências
- **Positivas**: Integridade relacional garantida diretamente pelo PostgreSQL; adição de novos estados com simples `INSERT` sem bloqueio DDL; rastreabilidade forense total com auditoria de eventos.
- **Trade-off**: Uma junção a mais por leitura (mitigada por índices e relacionamentos `lazy="selectin"` no ORM).
