from datetime import date, datetime
from decimal import Decimal
import hashlib
import hmac
import json
from typing import Optional

from connectors.payment_connector import PaymentConnector
from controllers.base_controller import BaseController
from dtos.charge_dto import ChargeDTO
from errors.custom_errors import InvalidSignature, NotFoundAccount, NotFoundCharge
from models.charge import Charge
from repositories.account_repository import AccountRepository
from repositories.charge_repository import ChargeRepository
from repositories.credit_repository import CreditRepository
from repositories.ledger_repository import LedgerRepository
from repositories.pocket_repository import PocketRepository


class ChargeController(BaseController):
    WEBHOOK_SECRET = "qitech_bootcamp_secret_2026"

    def __init__(self) -> None:
        super().__init__(__name__)
        self.charge_repository = ChargeRepository(self.context)
        self.account_repository = AccountRepository(self.context)
        self.ledger_repository = LedgerRepository(self.context)
        self.credit_repository = CreditRepository(self.context)
        self.pocket_repository = PocketRepository(self.context)
        self.payment_connector = PaymentConnector()

    def create_charge(self, account_key: str, payload: dict) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)

        method = payload["method"]
        amount = payload["amount"]
        due_date = date.fromisoformat(payload["due_date"])
        customer_document = payload.get("customer_document")
        metadata = payload.get("metadata")

        # Cálculo da taxa operacional (ADR-0008)
        if method == "PIX":
            fee_amount = 90  # R$ 0,90
        elif method == "BOLETO":
            fee_amount = 250  # R$ 2,50
        elif method == "CREDIT_CARD_LINK":
            fee_amount = int(amount * 0.0299)  # 2,99%
        else:
            fee_amount = 0

        charge = self.charge_repository.create_charge(
            account_id=account.id,
            method_enum=method,
            amount=amount,
            fee_amount=fee_amount,
            due_date=due_date,
            customer_document=customer_document,
            metadata=metadata,
        )

        # Registro no parceiro externo de compensação/adquirente
        self.payment_connector.create_charge(
            method=method,
            amount=amount,
            due_date=str(due_date),
            customer_document=customer_document,
        )

        return ChargeDTO.obj_to_dict(charge)

    def get_charge(self, charge_key: str) -> dict:
        charge = self.charge_repository.get_by_key(charge_key)
        if not charge:
            raise NotFoundCharge(charge_key)
        return ChargeDTO.obj_to_dict(charge)

    def _settle_charge(self, charge: Charge) -> dict:
        """Executa a liquidação contábil, deduções e atualizações do ecossistema."""
        # 1. Atualiza status da cobrança para 'paid'
        self.charge_repository.update_status(charge.id, "paid", paid_at=datetime.now())

        # 2. Liquidação bruta + débito atômico de taxa no Ledger (ADR-0008)
        account = charge.account
        tx_type = "PIX_CASH_IN" if charge.method.enumerator == "PIX" else "BOLETO_CASH_IN"
        self.ledger_repository.execute_cash_in(
            dest_account=account,
            amount=charge.amount,
            fee_amount=charge.fee_amount,
            type_enum=tx_type,
            description=f"Liquidação de cobrança {charge.method.enumerator}",
        )

        # 3. Trava de Recebíveis se houver contrato de crédito ativo (RFC 05)
        active_contract = self.credit_repository.get_active_contract_for_pj(account.id)
        retained_amount = 0
        if active_contract and active_contract.pocket_id:
            retention_rate = float(active_contract.retention_percentage) / 100.0
            retained_amount = int(charge.amount * retention_rate)
            if retained_amount > 0 and account.balance >= retained_amount:
                # Transfere da conta PJ para a caixinha de trava
                account.balance -= retained_amount
                self.pocket_repository.update_pocket_balance(active_contract.pocket_id, retained_amount)

        # 4. Atualiza Revenue Tracker MEI (RFC 07)
        self.pocket_repository.add_revenue(
            customer_id=account.customer_id,
            year=datetime.now().year,
            amount=charge.amount,
        )

        return {
            "charge_key": charge.charge_key,
            "net_amount": charge.net_amount,
            "retained_for_credit": retained_amount,
        }

    def process_webhook(self, payload: dict, signature: Optional[str] = None) -> dict:
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        expected_sig = hmac.new(self.WEBHOOK_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

        # Se assinatura enviada, valida HMAC
        if signature and signature != expected_sig:
            raise InvalidSignature()

        event = self.charge_repository.create_webhook_event(
            event_type=payload.get("event", "payment.settled"),
            payload=payload,
            signature=signature or expected_sig,
        )

        charge_key = payload.get("charge_key")
        charge = self.charge_repository.get_by_key(charge_key)
        if not charge:
            raise NotFoundCharge(charge_key)

        settle_result = self._settle_charge(charge)
        self.charge_repository.mark_webhook_processed(event.id)

        return {
            "status": "processed",
            "charge_key": charge.charge_key,
            "net_amount": settle_result["net_amount"],
            "retained_for_credit": settle_result["retained_for_credit"],
        }

    def reconcile_charges(self, payload: Optional[dict] = None) -> dict:
        """Job de conciliação ativa periódica (polling de saída) para boletos e pagamentos."""
        charge_keys = payload.get("charge_keys") if payload else None
        pending_charges = self.charge_repository.get_pending_charges(charge_keys=charge_keys)

        reconciled = []
        settled_amount = 0

        for charge in pending_charges:
            status_info = self.payment_connector.check_charge_status(
                charge.charge_key,
                charge.method.enumerator,
            )
            if status_info.get("status") == "PAID":
                result = self._settle_charge(charge)
                reconciled.append(result)
                settled_amount += charge.amount

        return {
            "reconciled_count": len(reconciled),
            "settled_amount": settled_amount,
            "charges": reconciled,
        }

