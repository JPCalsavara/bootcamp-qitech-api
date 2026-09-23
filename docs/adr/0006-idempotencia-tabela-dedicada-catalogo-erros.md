# ADR-0006: Idempotência Estrita em Tabela Dedicada e Catálogo Semântico de Erros

| | |
|---|---|
| **Status** | **Aprovado** |
| **Data** | 19/09/2026 |
| **Decisores** | João Pedro Calsavara / Engenharia Core Banking |
| **Tags** | `idempotencia`, `resiliencia`, `catalogo-erros`, `ttl` |

---

## Contexto
Redes móveis e conexões de internet são inerentemente instáveis. Quando um cliente envia `POST /transactions` e a conexão cai antes de receber a resposta, o cliente tende a retentar. Sem idempotência, a conta sofrerá débito duplicado. Adicionalmente, retornar apenas status HTTP genéricos (como 400 seco) impede que sistemas automatizados tratem a falha programaticamente.

## Decisão
1. **Tabela Dedicada de Idempotência (`idempotency_record`):** As requisições financeiras exigem o cabeçalho HTTP `Idempotency-Key` e são registradas em tabela desacoplada contendo chave, hash SHA-256 do payload, código de resposta HTTP, corpo de resposta e TTL de 24 horas. Requisições repetidas com o mesmo payload retornam o resultado em cache imediatamente (tanto para sucessos quanto para falhas de validação); se o payload divergir, rejeita com `409 Conflict (QIT001008)`.
2. **Catálogo de Erros Semânticos:** Todo erro da aplicação retorna um corpo estruturado inspirado na RFC 9457 (Problem Details), com código único e imutável de negócio:
   - `QIT000...`: Erros de protocolo e infraestrutura (JSON inválido, ausência de token, PIN incorreto).
   - `QIT001...`: Erros de negócio da API (Saldo insuficiente, documento inválido, conta inativa, etc.).

## Consequências
- **Positivas**: Eliminação total de débitos acidentais por retentativas de rede; previsibilidade para clientes e parceiros integradores.
- **Trade-off**: Uma consulta a mais antes de processar a requisição e limpeza periódica de registros expirados (TTL).
