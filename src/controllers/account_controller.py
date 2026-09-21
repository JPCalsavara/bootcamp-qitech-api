from typing import List
from controllers.base_controller import BaseController
from dtos.account_dto import AccountDTO
from errors.custom_errors import (
    AccountClosePositiveBalance,
    AccountStatusNotFound,
    CustomerNotActive,
    InsufficientFunds,
    InvalidOperation,
    NotFoundAccount,
    NotFoundCustomer,
    SampleEntityFinalStatus,
)
from repositories.account_repository import AccountRepository
from repositories.customer_repository import CustomerRepository


class AccountController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.customer_repository = CustomerRepository(self.context)

    def create_twin_accounts(self, customer_key: str) -> List[dict]:
        self.logger.debug(f"Provisionando contas vinculadas para customer_key={customer_key}")
        customer = self.customer_repository.get_by_key(customer_key)
        if not customer:
            raise NotFoundCustomer(customer_key)

        # Contas podem ser criadas após aprovação ou no fluxo
        accounts = self.account_repository.create_twin_accounts(customer.id)
        return [AccountDTO.obj_to_dict(acc) for acc in accounts]

    def get_by_key(self, account_key: str) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)
        return AccountDTO.obj_to_dict(account)

    def get_by_customer(self, customer_key: str) -> List[dict]:
        customer = self.customer_repository.get_by_key(customer_key)
        if not customer:
            raise NotFoundCustomer(customer_key)
        accounts = self.account_repository.get_by_customer_id(customer.id)
        return [AccountDTO.obj_to_dict(acc) for acc in accounts]

    def get_balance(self, account_key: str) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)
        blocked = getattr(account, "blocked_balance", 0) or 0
        return {
            "account_key": account.account_key,
            "balance": account.balance,
            "blocked_balance": blocked,
            "available_balance": account.balance - blocked,
            "account_number": account.account_number,
            "type": account.account_type.enumerator,
        }

    def update_status(self, account_key: str, payload: dict) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)

        to_status_enum = payload.get("status")
        reason_code = payload.get("reason_code", "VOLUNTARY")
        to_status = self.account_repository.get_status(to_status_enum)
        if not to_status:
            raise AccountStatusNotFound(to_status_enum)

        # 1. Se já está em status final 'closed', rejeita
        if account.status.enumerator == "closed":
            raise SampleEntityFinalStatus(account.status.enumerator, to_status_enum)


        # 2. Se está tentando encerrar ('closed'):
        if to_status_enum == "closed":
            # Exceção para compliance / fraude (Resolução BCB 518/2025)
            is_compliance_force = reason_code in ["COMPLIANCE_FRAUD", "IRREGULARITY_BCB518"]
            if not is_compliance_force and account.balance > 0:
                raise AccountClosePositiveBalance(account.balance)

        updated_account = self.account_repository.update_status(account.id, to_status_enum, reason_code)
        return {
            "account_key": updated_account.account_key,
            "status": updated_account.status.enumerator,
            "balance": updated_account.balance,
            "blocked_balance": getattr(updated_account, "blocked_balance", 0) or 0,
        }

    def update_blocked_balance(self, account_key: str, payload: dict) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)

        operation = payload.get("operation")
        amount = payload.get("amount", 0)

        if amount <= 0:
            raise InvalidOperation("Valor de bloqueio deve ser maior que zero")

        current_blocked = getattr(account, "blocked_balance", 0) or 0

        if operation == "BLOCK":
            available = account.balance - current_blocked
            if available < amount:
                raise InsufficientFunds("Saldo disponível insuficiente para bloqueio cautelar")
            new_blocked = current_blocked + amount
        elif operation == "UNBLOCK":
            if current_blocked < amount:
                raise InvalidOperation("Valor de desbloqueio maior que o saldo bloqueado atual")
            new_blocked = current_blocked - amount
        else:
            raise InvalidOperation(f"Operação desconhecida: {operation}")

        updated_account = self.account_repository.update_blocked_balance(account.id, new_blocked)
        return {
            "account_key": updated_account.account_key,
            "balance": updated_account.balance,
            "blocked_balance": updated_account.blocked_balance,
            "available_balance": updated_account.balance - updated_account.blocked_balance,
        }

