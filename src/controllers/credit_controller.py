from decimal import Decimal
from typing import Optional

from controllers.base_controller import BaseController
from dtos.credit_dto import CreditContractDTO, ReceivablesAnticipationDTO
from errors.custom_errors import NotFoundAccount, NotFoundCreditContract, NotFoundCustomer
from repositories.account_repository import AccountRepository
from repositories.credit_repository import CreditRepository
from repositories.customer_repository import CustomerRepository
from repositories.ledger_repository import LedgerRepository
from repositories.pocket_repository import PocketRepository


class CreditController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.credit_repository = CreditRepository(self.context)
        self.customer_repository = CustomerRepository(self.context)
        self.account_repository = AccountRepository(self.context)
        self.pocket_repository = PocketRepository(self.context)
        self.ledger_repository = LedgerRepository(self.context)

    def contract_credit(self, payload: dict) -> dict:
        customer_key = payload["customer_key"]
        pj_key = payload["account_pj_key"]
        pf_key = payload["account_pf_key"]
        requested_amount = payload["requested_amount"]
        term_months = payload["term_months"]
        interest_rate = Decimal(str(payload["interest_rate_monthly"]))
        retention_percentage = Decimal(str(payload["retention_percentage"]))

        customer = self.customer_repository.get_by_key(customer_key)
        if not customer:
            raise NotFoundCustomer(customer_key)

        account_pj = self.account_repository.get_by_key(pj_key)
        if not account_pj:
            raise NotFoundAccount(pj_key)

        account_pf = self.account_repository.get_by_key(pf_key)
        if not account_pf:
            raise NotFoundAccount(pf_key)

        # Caixinha de Trava de Crédito
        pockets = self.pocket_repository.get_pockets_by_account_id(account_pj.id)
        credit_pocket = next((p for p in pockets if p.pocket_type.enumerator == "TRAVA_CREDITO"), None)
        if not credit_pocket:
            credit_pocket = self.pocket_repository.create_pocket(
                account_id=account_pj.id,
                type_enum="TRAVA_CREDITO",
                name="Trava de Crédito CCB",
                target_amount=0,
                is_locked=True,
            )

        contract = self.credit_repository.create_contract(
            customer_id=customer.id,
            account_pj_id=account_pj.id,
            account_pf_id=account_pf.id,
            requested_amount=requested_amount,
            interest_rate_monthly=interest_rate,
            term_months=term_months,
            retention_percentage=retention_percentage,
            pocket_id=credit_pocket.id,
        )

        # Desembolso do valor na conta PJ (RFC 05)
        self.ledger_repository.execute_cash_in(
            dest_account=account_pj,
            amount=requested_amount,
            type_enum="CREDIT_DISBURSEMENT",
            description=f"Desembolso de Crédito CCB {contract.contract_key}",
        )

        return CreditContractDTO.obj_to_dict(contract)

    def get_contract(self, contract_key: str) -> dict:
        contract = self.credit_repository.get_by_key(contract_key)
        if not contract:
            raise NotFoundCreditContract(contract_key)
        return CreditContractDTO.obj_to_dict(contract)

    def anticipate_receivables(self, payload: dict) -> dict:
        acc_key = payload["account_key"]
        charge_keys = payload["charge_keys"]
        discount_rate = Decimal(str(payload["discount_rate"]))

        account = self.account_repository.get_by_key(acc_key)
        if not account:
            raise NotFoundAccount(acc_key)

        # Simulação: cada cobrança vale R$ 1.000,00 se valor não for recuperado
        total_original = 100000 * len(charge_keys)
        discount_fee = int(Decimal(total_original) * discount_rate)
        net_amount = total_original - discount_fee

        anticipation = self.credit_repository.create_anticipation(
            account_id=account.id,
            original_amount=total_original,
            discount_fee=discount_fee,
            charge_ids=charge_keys,
        )

        # Desembolso do adiantamento
        self.ledger_repository.execute_cash_in(
            dest_account=account,
            amount=net_amount,
            type_enum="RECEIVABLES_ANTICIPATION",
            description="Liquidação de Antecipação de Recebíveis",
        )

        return ReceivablesAnticipationDTO.obj_to_dict(anticipation)
