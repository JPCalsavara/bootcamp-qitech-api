# CoreBank MEI - Contexto de Domínio

API de Core Banking focada em Microempreendedores Individuais (MEI), provendo ledger contábil de partidas dobradas, separação patrimonial PF/PJ, envelopes de retenção tributária e proteção de fluxo de caixa.

## Language

### Entidades Principais

**Customer**:
O Microempreendedor Individual (MEI) cadastrado no sistema, detentor do CPF e do CNPJ, titular das contas vinculadas PF e PJ.
_Avoid_: Party, User, Client, MerchantProfile


**Account**:
A conta de pagamento custodiada pelo sistema, com saldo em centavos e ciclo de vida estrito.
_Avoid_: Wallet, Carteira

**PersonalAccount**:
A conta bancária da Pessoa Física utilizada para despesas pessoais e recebimento de pró-labore/lucro.
_Avoid_: Conta Corrente PF, Conta Pessoal

**BusinessAccount**:
A conta bancária da Pessoa Jurídica utilizada exclusivamente para operações do negócio (recebimentos de clientes e despesas da empresa).
_Avoid_: Conta Jurídica, Conta PJ

**Pocket**:
Subconta ou envelope de retenção dentro de uma `BusinessAccount` para provisionamento automático (ex: DAS-MEI, fornecedores, emergência).
_Avoid_: Caixinha, Cofrinho, Envelope

**TransferPolicy**:
Regra de conformidade que estipula o teto máximo de retiradas mensais da `BusinessAccount` para a `PersonalAccount`, preservando o capital de giro.
_Avoid_: Limite, Trava, Regra de Saque

**RevenueTracker**:
Acumulador do faturamento bruto anual da empresa para monitorar a proximidade do teto regulatório do MEI (R$ 81.000/ano).
_Avoid_: Faturamento, Contador Fiscal

**LedgerEntry**:
Lançamento contábil imutável de débito ou crédito que compõe o livro-razão de partidas dobradas.
_Avoid_: Movimentação, Histórico

**Transaction**:
Operação financeira bilateral que transfere fundos entre duas contas, originando lançamentos simétricos no ledger.
_Avoid_: Transfer, Pagamento

**TransactionPin**:
Código numérico de quatro dígitos criptografado, exigido exclusivamente para autorizar a liquidação de transferências financeiras.
_Avoid_: Senha de transação, Token de saque

**IdempotencyRecord**:
Registro persistido de idempotência contendo a chave, hash da requisição, código HTTP e resposta em cache com expiração de 24 horas.
_Avoid_: Cache de requisição, Trava de duplicidade

**SettlementAccount**:
Conta contábil interna do sistema bancário utilizada como contrapartida para liquidação de depósitos (cash-in) e saques (cash-out).
_Avoid_: Conta mãe, Conta transitória, Conta gráfica

**BlockedBalance**:
Parcela do saldo da conta retida cautelarmente por suspeita de fraude ou ordem judicial, indisponível para débitos.
_Avoid_: Saldo congelado, Trava de saldo

**ProfitDistribution**:
Transferência interna de recursos da BusinessAccount para a PersonalAccount do mesmo Customer, classificada como lucro isento de IRPF conforme a Lei Complementar nº 123/2006.
_Avoid_: Pró-labore, Retirada, Sangria de caixa

