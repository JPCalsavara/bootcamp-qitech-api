# ADR-0004: Arquitetura Contábil Imutável com Partidas Dobradas (Append-Only)

| | |
|---|---|
| **Status** | **Aprovado** |
| **Data** | 19/09/2026 |
| **Decisores** | João Pedro Calsavara / Engenharia Core Banking |
| **Tags** | `ledger`, `partidas-dobradas`, `append-only`, `contabilidade` |

---

## Contexto
Sistemas financeiros tradicionais costumam alterar o saldo da conta diretamente com `UPDATE account SET balance = ...`. Isso destrói o histórico de como o saldo foi construído e inviabiliza auditorias contábeis. A exclusão lógica (*soft delete* com flag `is_deleted`) é um antipadrão que viola restrições de unicidade e esconde mutações destrutivas.

## Decisão
1. Implementar o padrão canônico de **Partidas Dobradas (*Double-Entry Bookkeeping*)**: toda movimentação financeira gera no mínimo dois lançamentos na tabela imutável `ledger_entry` (um `DEBIT` e um `CREDIT` de mesmo valor).
2. Tabela `ledger_entry` é estritamente **Append-Only**: nenhuma linha recebe `UPDATE` ou `DELETE`.
3. O saldo na tabela `account` é mantido como uma visão materializada atualizada atomicamente na mesma transação para leitura de alta performance, assegurada por `CONSTRAINT check_positive_balance CHECK (balance_cents >= 0)`.
4. Estornos e correções não apagam o lançamento original: geram uma nova transação de estorno (*reversal*) com lançamentos inversos.

## Consequências
- **Positivas**: Auditoria e conciliação contínua: o saldo de qualquer conta é verificável por $\sum(\text{Créditos}) - \sum(\text{Débitos})$; integridade forense contra fraudes internas.
- **Trade-off**: Maior volume de escrita em banco de dados compensado por integridade inegociável.
