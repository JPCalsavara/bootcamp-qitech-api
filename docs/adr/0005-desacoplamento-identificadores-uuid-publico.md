# ADR-0005: Desacoplamento de Identificadores com UUID Público e Mitigação de IDOR

## Contexto
Expor chaves primárias sequenciais do banco de dados (`id: 1, 2, 3...`) permite ataques de enumeração horizontal (*Insecure Direct Object Reference* - IDOR), nos quais um invasor descobre o volume de clientes da instituição ou tenta consultar transações alheias alterando o parâmetro da URL. Além disso, retornar `403 Forbidden` quando um recurso de terceiro é acessado confirma para o atacante que aquele recurso existe.

## Decisão
1. **Separação de Chaves:** O banco utiliza inteiros sequenciais (`SERIAL / INTEGER`) estritamente como chaves primárias e estrangeiras internas para máxima eficiência de índices e joins. Todas as entidades expõem externamente um UUIDv4 único (`customer_key`, `account_key`, `transaction_key`).
2. **Mitigação de IDOR:** Consultas a recursos que não pertencem ao usuário autenticado respondem uniformemente com `HTTP 404 Not Found` (em vez de `403 Forbidden`). O cliente não tem como distinguir entre um identificador inexistente e um identificador pertencente a outro cliente.

## Consequências
- **Positivas**: Elimina riscos de enumeração de dados de clientes e espionagem de volume transacional; preserva performance de junções no PostgreSQL.
- **Trade-off**: Necessidade de manter dois identificadores (interno numérico e público UUID) nas tabelas principais.
