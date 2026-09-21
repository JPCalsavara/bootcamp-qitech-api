from errors import QIException


class NotFoundSampleEntity(QIException):
    code = "QIT001001"

    def __init__(self, sample_entity_key) -> None:
        title = "Entity not Found"
        http_status = 404
        description = f"Entity with key {sample_entity_key} was not found."
        translation = f"A entidade com chave {sample_entity_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class SampleEntityFinalStatus(QIException):
    code = "QIT001002"

    def __init__(self, old_status, new_status) -> None:
        title = "Entity cannot change status"
        http_status = 409
        description = f"Entity with status {old_status} cannot update to {new_status}."
        translation = "Essa entidade não pode ser atualizada."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDocumentNumber(QIException):
    """O CPF tem o formato certo e não existe.

    422, e não 400, de propósito: 400 quer dizer "não consegui ler o seu
    pedido". Aqui a API leu, entendeu, e o valor é que não pode existir —
    os dois últimos dígitos não batem com a conta. A diferença está
    explicada em src/utils/document_number.py.
    """

    code = "QIT001003"

    def __init__(self, document_number) -> None:
        title = "Invalid Document Number"
        http_status = 422
        description = f"The document number {document_number} is not a valid CPF."
        translation = "O CPF informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedDocumentNumber(QIException):
    """Já existe um cadastro com este CPF.

    409 Conflict: o pedido está correto em si, e o que impede é o que já
    está no banco. É a mesma família do SampleEntityFinalStatus aqui em
    cima — conflito com o que já existe, não erro de quem pediu.
    """

    code = "QIT001004"

    def __init__(self, document_number) -> None:
        title = "Document Number already registered"
        http_status = 409
        description = f"There is already an entity with the document number {document_number}."
        translation = "Já existe um cadastro com este CPF."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedEmail(QIException):
    code = "QIT001005"

    def __init__(self, email) -> None:
        title = "Email already registered"
        http_status = 409
        description = f"There is already an entity with the email {email}."
        translation = "Já existe um cadastro com este e-mail."
        super().__init__(title, self.code, http_status, description, translation)


class UnderageSampleEntity(QIException):
    code = "QIT001006"

    def __init__(self, age, minimum_age) -> None:
        title = "Entity is underage"
        http_status = 422
        description = f"The entity is {age} years old, and the minimum is {minimum_age}."
        translation = f"É preciso ter pelo menos {minimum_age} anos."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidBirthdate(QIException):
    """A data tem o formato certo e não existe no calendário.

    Existe porque o `pattern` do schema sabe contar dígitos, não dias:
    "2025-02-30" e "9999-99-99" passam pelo regex e morrem no
    `date.fromisoformat`. Sem esta classe, esse ValueError virava 500 —
    a API culpando a si mesma por um erro de quem chamou.
    """

    code = "QIT001007"

    def __init__(self, birthdate) -> None:
        title = "Invalid Birthdate"
        http_status = 422
        description = f"The birthdate {birthdate} is not a real date."
        translation = "A data de nascimento informada não existe."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidCNPJ(QIException):
    code = "QIT001008"

    def __init__(self, cnpj) -> None:
        title = "Invalid CNPJ"
        http_status = 422
        description = f"The document number {cnpj} is not a valid CNPJ."
        translation = "O CNPJ informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedCNPJ(QIException):
    code = "QIT001009"

    def __init__(self, cnpj) -> None:
        title = "CNPJ already registered"
        http_status = 409
        description = f"There is already an entity with the CNPJ {cnpj}."
        translation = "Já existe um cadastro com este CNPJ."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundCustomer(QIException):
    code = "QIT002001"

    def __init__(self, customer_key) -> None:
        title = "Customer not Found"
        http_status = 404
        description = f"Customer with key {customer_key} was not found."
        translation = f"O cliente com chave {customer_key} não foi encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundAccount(QIException):
    code = "QIT002002"

    def __init__(self, account_key) -> None:
        title = "Account not Found"
        http_status = 404
        description = f"Account with key {account_key} was not found."
        translation = f"A conta com chave {account_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundCharge(QIException):
    code = "QIT002003"

    def __init__(self, charge_key) -> None:
        title = "Charge not Found"
        http_status = 404
        description = f"Charge with key {charge_key} was not found."
        translation = f"A cobrança com chave {charge_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundCreditContract(QIException):
    code = "QIT002004"

    def __init__(self, contract_key) -> None:
        title = "Credit Contract not Found"
        http_status = 404
        description = f"Credit contract with key {contract_key} was not found."
        translation = f"O contrato de crédito com chave {contract_key} não foi encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class InsufficientFunds(QIException):
    code = "QIT002005"

    def __init__(self, message="Saldo insuficiente") -> None:
        title = "Insufficient Funds"
        http_status = 422
        description = message
        translation = "Saldo insuficiente para realizar a transação."
        super().__init__(title, self.code, http_status, description, translation)


class CustomerNotActive(QIException):
    code = "QIT002006"

    def __init__(self, status) -> None:
        title = "Customer not Active"
        http_status = 422
        description = f"Customer is in status {status} and cannot perform this operation."
        translation = "O cliente não está ativo para realizar esta operação."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidOperation(QIException):
    code = "QIT002007"

    def __init__(self, message) -> None:
        title = "Invalid Operation"
        http_status = 422
        description = message
        translation = message
        super().__init__(title, self.code, http_status, description, translation)


class InvalidSignature(QIException):
    code = "QIT002008"

    def __init__(self) -> None:
        title = "Invalid Webhook Signature"
        http_status = 401
        description = "The webhook HMAC signature is invalid."
        translation = "A assinatura HMAC do webhook é inválida."
        super().__init__(title, self.code, http_status, description, translation)


class PolicyViolation(QIException):
    code = "QIT002009"

    def __init__(self, message) -> None:
        title = "Policy Violation"
        http_status = 422
        description = message
        translation = message
        super().__init__(title, self.code, http_status, description, translation)



class AccountClosePositiveBalance(QIException):
    code = "QIT001011"

    def __init__(self, balance) -> None:
        title = "Account Has Residual Balance"
        http_status = 409
        description = f"Account has positive balance of {balance} cents and cannot be closed voluntarily."
        translation = "Conta possui saldo residual positivo e não pode ser encerrada voluntariamente."
        super().__init__(title, self.code, http_status, description, translation)


class AccountStatusNotFound(QIException):
    code = "QIT002010"

    def __init__(self, status) -> None:
        title = "Account Status Not Found"
        http_status = 400
        description = f"Status {status} is not a valid account status."
        translation = f"O status {status} não é um status de conta válido."
        super().__init__(title, self.code, http_status, description, translation)



