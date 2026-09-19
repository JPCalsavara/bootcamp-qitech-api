# Instruções para Agentes de IA

Este repositório utiliza as convenções e habilidades de engenharia assistida por IA (Matt Pocock Skills).

## Agent skills

### Issue tracker

Arquivos markdown locais sob `.scratch/<feature>/`. Consulte `docs/agents/issue-tracker.md`.

### Triage labels

Papéis canônicos de triagem mapeados 1:1 (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). Consulte `docs/agents/triage-labels.md`.

### Domain docs

Repositório de contexto único (`CONTEXT.md` e `docs/adr/` na raiz). Consulte `docs/agents/domain.md`.

## Padrões de Desenvolvimento e Testes

- **Apenas Testes de Integração**: Conforme o [ADR-0001](docs/adr/0001-apenas-testes-de-integracao.md), não crie testes unitários isolados com mocks. Todo teste deve ser de integração ponta a ponta (`tests/integration/`) exercitando os endpoints com banco de dados real.

