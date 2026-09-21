from datetime import date, datetime
from typing import Optional
from uuid import uuid4

from database import Context
from models import Customer, CustomerStatus, CustomerStatusEvent


class CustomerRepository:
    """Camada de persistência para Customer e máquina de estados de onboarding."""

    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_status(self, enumerator: str) -> Optional[CustomerStatus]:
        return self.session.query(CustomerStatus).filter(CustomerStatus.enumerator == enumerator).first()

    def get_by_key(self, customer_key: str) -> Optional[Customer]:
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def get_by_email(self, email: str) -> Optional[Customer]:
        return self.session.query(Customer).filter(Customer.email == email).first()

    def get_by_cpf(self, cpf: str) -> Optional[Customer]:
        return self.session.query(Customer).filter(Customer.cpf == cpf).first()

    def get_by_cnpj(self, cnpj: str) -> Optional[Customer]:
        return self.session.query(Customer).filter(Customer.cnpj == cnpj).first()

    def create(self, customer_data: dict, password_hash: str, pin_hash: str) -> Customer:
        customer = Customer()
        customer.customer_key = str(uuid4())
        customer.name = customer_data["name"]
        customer.legal_name = customer_data["legal_name"]
        customer.email = customer_data["email"]
        customer.cpf = customer_data["cpf"]
        customer.cnpj = customer_data["cnpj"]
        customer.birthdate = date.fromisoformat(customer_data["birthdate"])
        customer.phone = customer_data["phone"]
        customer.password_hash = password_hash
        customer.pin_hash = pin_hash

        status = self.get_status(CustomerStatus.CREATED)
        customer.status = status

        self.session.add(customer)
        self.session.flush()

        initial_event = CustomerStatusEvent()
        initial_event.customer_id = customer.id
        initial_event.from_status_id = None
        initial_event.to_status_id = status.id
        initial_event.reason_code = "ONBOARDING_INITIATED"
        initial_event.reason_detail = {"source": "HTTP_API"}
        initial_event.event_datetime = datetime.now()

        self.session.add(initial_event)
        self.session.commit()

        return customer
