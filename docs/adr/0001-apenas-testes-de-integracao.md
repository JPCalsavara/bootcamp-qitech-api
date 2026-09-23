# ADR-0001: Adoção Exclusiva de Testes de Integração (Sem Testes Unitários Isolados)

| | |
|---|---|
| **Status** | **Aprovado** |
| **Data** | 19/09/2026 |
| **Decisores** | João Pedro Calsavara / Engenharia Core Banking |
| **Tags** | `testes`, `qualidade`, `postgresql`, `fastapi` |

---

## Contexto
Em sistemas de Core Banking e serviços financeiros com livros-razão (*ledger*) de partidas dobradas e controle de concorrência, a maior parte dos bugs críticos e incidentes decorre de:
- Falhas de integridade referencial e constraints no banco de dados.
- Comportamentos inesperados em transações sob concorrência e isolamento (`SELECT FOR UPDATE`, locks).
- Divergências entre schemas de validação (Pydantic), mapeamento relacional (SQLAlchemy) e respostas HTTP.

Testes unitários isolados com mocks extensivos simulam o banco de dados e a camada HTTP, oferecendo falsa sensação de segurança sem testar as garantias ACID reais nem o contrato efetivo da API.

## Decisão
Adotamos como padrão obrigatório para o projeto **apenas testes de integração**, dispensando testes unitários isolados com mocks:
1. Todo teste deve exercitar o fluxo ponta a ponta através das rotas da API (usando `TestClient` do FastAPI) ou de serviços integrados com um banco de dados real de teste.
2. Não criaremos suites de testes unitários que mockam o banco de dados, repositórios ou transações.
3. Testes devem verificar a persistência real no PostgreSQL, os lançamentos contábeis de débito e crédito no ledger e os status codes/payloads HTTP.

## Consequências
- **Positivas**: Confiança máxima nas transações financeiras, validação real de migrations e constraints, sem manutenção de mocks frágeis.
- **Trade-off**: A execução da suite de testes depende de um container de banco de dados e é ligeiramente mais lenta do que testes unitários puros em memória, mas o ganho de confiabilidade contábil é indispensável para o domínio bancário.
