from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from database import Context
from models.credit import (
    CreditContract,
    CreditContractStatus,
    CreditInstallment,
    ReceivablesAnticipation,
)


class CreditRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_status(self, enumerator: str) -> Optional[CreditContractStatus]:
        return self.session.query(CreditContractStatus).filter(CreditContractStatus.enumerator == enumerator).first()

    def get_by_key(self, contract_key: str) -> Optional[CreditContract]:
        return self.session.query(CreditContract).filter(CreditContract.contract_key == contract_key).first()

    def create_contract(
        self,
        customer_id: int,
        account_pj_id: int,
        account_pf_id: int,
        requested_amount: int,
        interest_rate_monthly: Decimal,
        term_months: int,
        retention_percentage: Decimal,
        pocket_id: Optional[int] = None,
    ) -> CreditContract:
        status = self.get_status("disbursed")

        # Cálculo simples Price/juros compostos para o total
        rate = float(interest_rate_monthly)
        total_amount = int(requested_amount * ((1 + rate) ** term_months))

        contract = CreditContract()
        contract.contract_key = str(uuid4())
        contract.customer_id = customer_id
        contract.account_pj_id = account_pj_id
        contract.account_pf_id = account_pf_id
        contract.status_id = status.id
        contract.requested_amount = requested_amount
        contract.total_amount = total_amount
        contract.interest_rate_monthly = interest_rate_monthly
        contract.term_months = term_months
        contract.retention_percentage = retention_percentage
        contract.pocket_id = pocket_id

        self.session.add(contract)
        self.session.flush()

        # Cria as parcelas
        installment_amount = total_amount // term_months
        principal_part = requested_amount // term_months
        interest_part = installment_amount - principal_part

        today = date.today()
        for i in range(1, term_months + 1):
            installment = CreditInstallment()
            installment.installment_key = str(uuid4())
            installment.contract_id = contract.id
            installment.installment_number = i
            installment.amount = installment_amount
            installment.principal_amount = principal_part
            installment.interest_amount = interest_part
            installment.due_date = today + timedelta(days=30 * i)
            installment.status = "OPEN"
            self.session.add(installment)

        self.session.commit()
        return contract

    def get_active_contract_for_pj(self, account_pj_id: int) -> Optional[CreditContract]:
        disbursed_status = self.get_status("disbursed")
        active_status = self.get_status("active")
        status_ids = [s.id for s in [disbursed_status, active_status] if s]
        return (
            self.session.query(CreditContract)
            .filter(
                CreditContract.account_pj_id == account_pj_id,
                CreditContract.status_id.in_(status_ids),
            )
            .first()
        )

    def create_anticipation(
        self,
        account_id: int,
        original_amount: int,
        discount_fee: int,
        charge_ids: List[str],
    ) -> ReceivablesAnticipation:
        anticipation = ReceivablesAnticipation()
        anticipation.anticipation_key = str(uuid4())
        anticipation.account_id = account_id
        anticipation.original_amount = original_amount
        anticipation.discount_fee = discount_fee
        anticipation.net_disbursed_amount = original_amount - discount_fee
        anticipation.charge_ids = charge_ids
        anticipation.status = "COMPLETED"

        self.session.add(anticipation)
        self.session.commit()
        return anticipation

    def get_contracts_with_overdue_installments(
        self, cutoff_date: date, contract_key: Optional[str] = None
    ) -> List[CreditContract]:
        query = (
            self.session.query(CreditContract)
            .join(CreditInstallment)
            .filter(
                CreditInstallment.status.in_(["OPEN", "OVERDUE"]),
                CreditInstallment.due_date <= cutoff_date,
            )
        )
        if contract_key:
            query = query.filter(CreditContract.contract_key == contract_key)
        return query.distinct().all()

    def update_contract_status(self, contract: CreditContract, status_enum: str) -> None:
        status = self.get_status(status_enum)
        if status:
            contract.status_id = status.id
            self.session.flush()

