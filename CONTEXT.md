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

**CustomerStatus**:
Estado cadastral e de conformidade do Customer gerido por máquina de estados e tabela de domínio estrita.
_Avoid_: UserStatus, EstadoCivil, ClientStatus

**CustomerStatusEvent**:
Registro imutável e auditável de cada mudança de estado cadastral do Customer, contendo motivação e metadados de bureaus.
_Avoid_: StatusLog, CustomerHistory, LogCadastro

**Charge**:
Instrumento de cobrança comercial emitido pela BusinessAccount para recebimento de clientes via PIX dinâmico, Boleto Híbrido ou Link de Pagamento.
_Avoid_: Invoice, Fatura, CobrancaExterna

**FeeRevenueAccount**:
Conta contábil interna do sistema bancário utilizada como contrapartida para apropriação de receitas de tarifas transacionais e spreads.
_Avoid_: ContaLucro, ContaTaxas, CaixaFintech

**CreditContract**:
Contrato formal de crédito vinculado à BusinessAccount (Cédula de Crédito Bancário - CCB), detalhando parcelas, juros e taxa de retenção.
_Avoid_: Emprestimo, Financiamento, Divida

**AmortizationPocket**:
Subconta ou envelope de retenção vinculado à BusinessAccount, alimentado por um percentual automático de cada venda para amortizar parcelas de crédito.
_Avoid_: CofrinhoDivida, TravaCaixa, ReservaParcela

**ReceivablesAnticipation**:
Operação financeira de antecipação com desconto a valor presente de direitos creditórios futuros de vendas a prazo.
_Avoid_: Adiantamento, SaqueFuturo, ResgateAntecipado

**ChargebackClaim**:
Registro de obrigação de ressarcimento decorrente de contestação ou estorno de venda cujo saldo disponível da BusinessAccount era insuficiente para absorver o débito.
_Avoid_: SaldoNegativo, Rombo, DividaContestada

**CashSweep**:
Mecanismo automático e invisível de alocação de saldo ocioso da conta em títulos de renda fixa (CDB/RDB) com resgate instantâneo no momento de pagamentos ou transferências.
_Avoid_: VarreduraManual, InvestimentoManual, ResgateManual

**TreasuryYieldAccount**:
Conta contábil interna do sistema bancário utilizada como contrapartida para liquidação de rendimentos de liquidez diária (100% CDI) pagos aos clientes.
_Avoid_: ContaJuros, CaixaRendimento, ContaCDB

**YieldPosition**:
Registro de lote de saldo remunerado com carimbo de data/hora para controle de antiguidade, retenção de IOF, alíquota de IR e elegibilidade à regra de 30 dias.
_Avoid_: Investimento, AplicacaoCDB, TituloCliente

