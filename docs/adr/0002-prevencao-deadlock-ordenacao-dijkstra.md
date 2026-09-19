# ADR-0002: Prevenção de Deadlock Concorrente via Ordenação Global de Locks (Dijkstra)

## Contexto
Em transferências simultâneas entre contas cruzadas (ex: Alice transferindo para Bob e Bob transferindo para Alice no mesmo milissegundo), duas threads disputam locks de linha no PostgreSQL. Sem uma ordem pré-estabelecida, ocorre a clássica condição de Espera Circular (*Circular Wait*), gerando um Deadlock (`40P01`) e derrubando requisições com erro HTTP 500.

## Decisão
Implementar a **Hierarquia Global de Recursos de Dijkstra (1965)**: sempre que uma transação exigir lock de mais de uma conta (`SELECT ... FOR UPDATE`), os IDs internos devem ser ordenados deterministicamente em ordem crescente antes da query:
```python
ordered_ids = sorted([origin_id, destination_id])
locked_accounts = repo.lock_accounts_for_update(ordered_ids)
```

## Consequências
- **Positivas**: A espera circular torna-se matematicamente impossível; zero ocorrências de `DeadlockDetected (40P01)`.
- **Trade-off**: Custo de implementação de 1 linha de Python (`sorted(...)`), eliminando a necessidade de mecanismos complexos de retentativa com backoff.
