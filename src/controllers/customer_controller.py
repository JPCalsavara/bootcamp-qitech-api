import hashlib
from datetime import date

from controllers.base_controller import BaseController
from dtos.customer_dto import CustomerDTO
from errors import (
    DuplicatedCNPJ,
    DuplicatedDocumentNumber,
    DuplicatedEmail,
    InvalidBirthdate,
    InvalidDocumentNumber,
)
from repositories.customer_repository import CustomerRepository
from utils.document_number import is_valid_cpf


class CustomerController(BaseController):
    """Regras de negócio de Customer e Onboarding Seguro (RFC 03)."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)

    def create(self, customer_data: dict) -> dict:
        self.logger.debug("Iniciando onboarding de novo Customer")

        cpf = customer_data["cpf"]
        cnpj = customer_data["cnpj"]
        email = customer_data["email"]
        birthdate_str = customer_data["birthdate"]

        try:
            birthdate = date.fromisoformat(birthdate_str)
        except ValueError:
            raise InvalidBirthdate(birthdate_str)

        if not is_valid_cpf(cpf):
            raise InvalidDocumentNumber(cpf)

        if self.customer_repository.get_by_cpf(cpf) is not None:
            raise DuplicatedDocumentNumber(cpf)

        if self.customer_repository.get_by_email(email) is not None:
            raise DuplicatedEmail(email)

        if self.customer_repository.get_by_cnpj(cnpj) is not None:
            raise DuplicatedCNPJ(cnpj)

        # Hasheamento da senha e do PIN
        password_hash = hashlib.sha256(customer_data["password"].encode("utf-8")).hexdigest()
        pin_hash = hashlib.sha256(customer_data["transaction_pin"].encode("utf-8")).hexdigest()

        customer = self.customer_repository.create(
            customer_data=customer_data,
            password_hash=password_hash,
            pin_hash=pin_hash,
        )

        return CustomerDTO.obj_to_dict(customer)

    def get_by_key(self, customer_key: str) -> dict:
        customer = self.customer_repository.get_by_key(customer_key)
        if not customer:
            raise NotFoundCustomer(customer_key)
        return CustomerDTO.obj_to_dict(customer)

