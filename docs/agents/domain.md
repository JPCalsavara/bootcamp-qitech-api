# Documentação de Domínio (Domain Docs)

Como as skills de engenharia devem consumir a documentação de domínio deste repositório ao explorar a base de código.

## Antes de explorar, leia estes arquivos

- **`CONTEXT.md`** na raiz do repositório, ou
- **`CONTEXT-MAP.md`** na raiz do repositório caso exista — ele aponta para um `CONTEXT.md` por contexto delimitado. Leia cada um relevante para o tema.
- **`docs/adr/`** — leia os ADRs (Architectural Decision Records) que tocam na área em que você está prestes a trabalhar. Em repositórios multi-contexto, verifique também `src/<contexto>/docs/adr/` para decisões com escopo local.

Se algum desses arquivos não existir, **prossiga silenciosamente**. Não aponte a ausência deles como erro nem sugira criá-los antecipadamente. A skill `/domain-modeling` (acessada via `/grill-with-docs` e `/improve-codebase-architecture`) os cria sob demanda quando termos ou decisões forem efetivamente resolvidos.

## Estrutura de Arquivos

Repositório de contexto único (padrão para a maioria dos repositórios):

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

Repositório multi-contexto (identificado pela presença de `CONTEXT-MAP.md` na raiz):

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← decisões em nível de sistema
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← decisões específicas do contexto
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## Use o vocabulário do glossário

Quando a sua saída nomear um conceito de domínio (no título de uma issue, proposta de refatoração, hipótese, nome de teste), use o termo exatamente como definido no `CONTEXT.md`. Não desvie para sinônimos que o glossário explicitamente evita.

Se o conceito necessário ainda não estiver no glossário, isso é um sinal — ou você está inventando uma linguagem que o projeto não adota (reconsidere), ou há uma lacuna real (anote para resolver com `/domain-modeling`).

## Aponte conflitos com ADRs

Se a sua proposta ou código contradisser um ADR existente, exponha isso explicitamente em vez de sobrescrever silenciosamente:

> _Contradiz o ADR-0007 (pedidos com event sourcing) — mas vale reabrir a discussão porque…_
