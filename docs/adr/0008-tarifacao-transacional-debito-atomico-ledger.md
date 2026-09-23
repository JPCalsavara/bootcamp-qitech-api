# ADR-0008: Tarifação Transacional com Débito Atômico no Ledger (Gross + Fee Debit)

| | |
|---|---|
| **Status** | **Aprovado** |
| **Data** | 21/09/2026 |
| **Decisores** | João Pedro Calsavara / Engenharia Core Banking |
| **Tags** | `tarifacao`, `meios-de-pagamento`, `simples-nacional`, `partidas-dobradas` |

---

## Contexto
Gateways de pagamento e adquirentes convencionais costumam adotar a liquidação líquida direta (*Net Settlement*): ao liquidar uma venda de R$ 100,00 com tarifa de R$ 1,50, creditam diretamente R$ 98,50 na conta do cliente, registrando a taxa apenas como metadado ou desconto não escriturado.

Para o Microempreendedor Individual (MEI) e para um Core Banking, essa abordagem introduz distorções fiscais e contábeis graves:
1. **Divergência com a Nota Fiscal (NFS-e)**: O MEI emite a nota fiscal pelo valor cheio do serviço prestado (R$ 100,00). O extrato bancário precisa espelhar exatamente esse valor para conciliação contábil com a Receita Federal.
2. **Subdeclaração Involuntária de Faturamento**: Se o extrato registrar apenas o valor líquido, o MEI corre o risco de declarar faturamento a menor na DASN-SIMEI ou sofrer glosas contábeis.
3. **Opacidade na Receita da Fintech**: Lançar tarifas como mero desconto embutido sem partidas dobradas impede a conciliação automatizada da receita própria da instituição no livro-razão.

## Decisão
1. **Liquidação em Valor Bruto com Débito Atômico de Tarifa**:
   - Toda cobrança liquidada gera obrigatoriamente um crédito no valor facial total da venda (`amount_cents`) na `BusinessAccount` do MEI, com contrapartida de débito na `SettlementAccount` interna.
   - Imediatamente na mesma transação atômica do PostgreSQL (sob lock ordenado de Dijkstra conforme [ADR-0002](0002-prevencao-deadlock-ordenacao-dijkstra.md)), a taxa transacional pactuada (`fee_cents`) é debitada da `BusinessAccount` e creditada na conta contábil interna de receita (`FeeRevenueAccount`).
2. **Registro Explícito no Extrato**: O extrato do MEI exibe duas linhas distintas com carimbo temporal idêntico: o recebimento bruto da venda e a cobrança da tarifa da plataforma.
3. **Alimentação do Faturamento Fiscal**: O acumulador anual `RevenueTracker` é incrementado pelo valor **bruto** da venda, preservando a aderência ao teto regulatório de R$ 81.000,00 da LC 123/2006.

## Consequências
- **Positivas**: Conciliação fiscal perfeita para o MEI (extrato bate 1:1 com a NF-e); transparência total de custos; apropriação contábil auditável da receita da fintech em partidas dobradas ([ADR-0004](0004-arquitetura-contabil-partidas-dobradas.md)).
- **Trade-off**: Duas linhas de transação no ledger por recebimento comercial em vez de uma única linha líquida, compensado pela conformidade regulatória e contábil inegociável.
