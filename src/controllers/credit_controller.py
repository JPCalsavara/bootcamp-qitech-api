from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
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

    def contract_credit(self, payload: dict, idempotency_key: Optional[str] = None) -> dict:
        # 1. Idempotência (ADR-0006)
        if idempotency_key:
            cached = self.ledger_repository.get_idempotency(idempotency_key)
            if cached:
                return cached.response_body

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

        response_body = CreditContractDTO.obj_to_dict(contract)

        # Salva idempotência se chave fornecida (ADR-0006)
        if idempotency_key:
            req_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
            self.ledger_repository.save_idempotency(
                idempotency_key=idempotency_key,
                request_hash=req_hash,
                response_code=201,
                response_body=response_body,
            )

        self.context.db_session.commit()
        return response_body

    def get_contract(self, contract_key: str) -> dict:
        contract = self.credit_repository.get_by_key(contract_key)
        if not contract:
            raise NotFoundCreditContract(contract_key)
        return CreditContractDTO.obj_to_dict(contract)

    def anticipate_receivables(self, payload: dict, idempotency_key: Optional[str] = None) -> dict:
        # 1. Idempotência (ADR-0006)
        if idempotency_key:
            cached = self.ledger_repository.get_idempotency(idempotency_key)
            if cached:
                return cached.response_body

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

        response_body = ReceivablesAnticipationDTO.obj_to_dict(anticipation)

        # Salva idempotência se chave fornecida (ADR-0006)
        if idempotency_key:
            req_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
            self.ledger_repository.save_idempotency(
                idempotency_key=idempotency_key,
                request_hash=req_hash,
                response_code=201,
                response_body=response_body,
            )

        self.context.db_session.commit()
        return response_body

    def execute_cross_guarantee(self, payload: dict) -> dict:
        target_date_str = payload.get("target_date")
        target_date = date.fromisoformat(target_date_str) if target_date_str else date.today()
        contract_key = payload.get("contract_key")

        cutoff_date = target_date - timedelta(days=5)

        contracts = self.credit_repository.get_contracts_with_overdue_installments(
            cutoff_date=cutoff_date, contract_key=contract_key
        )

        settled_count = 0
        total_settled_amount = 0
        details = []
        processed_contract_keys = set()

        for contract in contracts:
            processed_contract_keys.add(contract.contract_key)
            overdue_installments = [
                inst
                for inst in contract.installments
                if inst.status in ["OPEN", "OVERDUE"] and inst.due_date <= cutoff_date
            ]
            overdue_installments.sort(key=lambda x: (x.due_date, x.installment_number))

            pf_acc = contract.account_pf
            pj_acc = contract.account_pj

            for installment in overdue_installments:
                needed = installment.amount - installment.paid_amount
                self.context.db_session.refresh(pf_acc)
                blocked = getattr(pf_acc, "blocked_balance", 0) or 0
                available = pf_acc.balance - blocked

                if available >= needed:
                    self.ledger_repository.execute_transfer(
                        source_account=pf_acc,
                        dest_account=pj_acc,
                        amount=needed,
                        type_enum="CREDIT_AMORTIZATION",
                        description=f"Compensação Garantia Cruzada MEI (CCB Art. 368 CC) Parc {installment.installment_number}",
                    )
                    installment.paid_amount += needed
                    installment.status = "PAID"
                    installment.paid_at = datetime.now()
                    self.context.db_session.flush()

                    settled_count += 1
                    total_settled_amount += needed
                    details.append(
                        {
                            "contract_key": contract.contract_key,
                            "installment_key": installment.installment_key,
                            "installment_number": installment.installment_number,
                            "amount_settled": needed,
                            "pf_account_key": pf_acc.account_key,
                            "status": "SETTLED",
                        }
                    )
                else:
                    installment.status = "OVERDUE"
                    self.credit_repository.update_contract_status(contract, "defaulted")
                    self.context.db_session.flush()
                    details.append(
                        {
                            "contract_key": contract.contract_key,
                            "installment_key": installment.installment_key,
                            "installment_number": installment.installment_number,
                            "amount_settled": 0,
                            "pf_account_key": pf_acc.account_key,
                            "status": "INSUFFICIENT_FUNDS_OVERDUE",
                        }
                    )

            if all(inst.status == "PAID" for inst in contract.installments):
                self.credit_repository.update_contract_status(contract, "settled")
            elif any(inst.status == "OVERDUE" for inst in contract.installments):
                self.credit_repository.update_contract_status(contract, "defaulted")
            else:
                self.credit_repository.update_contract_status(contract, "active")

        self.context.db_session.commit()

        return {
            "processed_contracts": len(processed_contract_keys),
            "settled_installments": settled_count,
            "total_settled_amount": total_settled_amount,
            "details": details,
        }

    def settle_due_installments(self, payload: Optional[dict] = None) -> dict:
        """RFC 04: Quitação automática de parcelas de CCB utilizando o saldo retido no Pocket de amortização."""
        payload = payload or {}
        target_date_str = payload.get("target_date")
        target_date = date.fromisoformat(target_date_str) if target_date_str else date.today()

        due_installments = self.credit_repository.get_due_installments(target_date)
        settled_count = 0
        total_settled_amount = 0
        details = []

        for installment in due_installments:
            contract = installment.contract
            if not contract or not contract.pocket_id:
                continue

            pocket = self.pocket_repository.get_by_id(contract.pocket_id)
            if not pocket:
                continue

            needed = installment.amount - installment.paid_amount
            if pocket.current_balance >= needed:
                self.pocket_repository.update_pocket_balance(contract.pocket_id, -needed)
                installment.paid_amount += needed
                installment.status = "PAID"
                installment.paid_at = datetime.now()
                self.context.db_session.flush()

                settled_count += 1
                total_settled_amount += needed
                details.append(
                    {
                        "contract_key": contract.contract_key,
                        "installment_key": installment.installment_key,
                        "installment_number": installment.installment_number,
                        "amount_settled": needed,
                        "status": "PAID_FROM_POCKET",
                    }
                )

                if all(inst.status == "PAID" for inst in contract.installments):
                    self.credit_repository.update_contract_status(contract, "settled")
                elif contract.status.enumerator != "active":
                    self.credit_repository.update_contract_status(contract, "active")

        self.context.db_session.commit()

        return {
            "processed_installments": len(due_installments),
            "settled_count": settled_count,
            "total_settled_amount": total_settled_amount,
            "details": details,
        }
