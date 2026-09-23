# ADR-0003: Representação Monetária em Centavos Inteiros (BIGINT) com 2 Casas Decimais

| | |
|---|---|
| **Status** | **Aprovado** |
| **Data** | 19/09/2026 |
| **Decisores** | João Pedro Calsavara / Engenharia Core Banking |
| **Tags** | `moeda`, `centavos`, `bigint`, `precisao-contabil` |

---

## Contexto
Representar valores monetários com tipos de ponto flutuante IEEE 754 (`FLOAT`, `DOUBLE`) gera resíduos de conversão binária (ex: `0.1 + 0.2 = 0.30000000000000004`). Em milhares de operações de débito e crédito, esses resíduos se acumulam, corrompendo balanços contábeis e gerando passivos regulatórios perante o Banco Central.

## Decisão
1. **No Banco de Dados:** Todos os campos de saldo, taxas e transações são colunas `BIGINT` representando centavos inteiros (R$ 10,00 = `1000`; R$ 0,01 = `1`).
2. **Na Aplicação:** Aritmética exclusivamente de números inteiros para operações de soma, subtração e checagem de saldo mínimo.
3. **Nos DTOs / Respostas da API:** A API expõe tanto o valor atômico inteiro (`balance_cents: 1000`) quanto a string decimal formatada com exatamente duas casas decimais (`balance: "10.00"`), garantindo consistência total para clientes web e mobile.

## Consequências
- **Positivas**: Erros de arredondamento eliminados na origem; performance nativa máxima de operações inteiras de 64 bits.
- **Trade-off**: Clientes da API que esperam float direto precisam ler o campo em centavos ou a string formatada.
