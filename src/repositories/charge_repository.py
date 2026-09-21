from datetime import date, datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from database import Context
from models.charge import Charge, ChargeMethod, ChargeStatus, ChargebackClaim, WebhookEvent


class ChargeRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_method(self, enumerator: str) -> Optional[ChargeMethod]:
        return self.session.query(ChargeMethod).filter(ChargeMethod.enumerator == enumerator).first()

    def get_status(self, enumerator: str) -> Optional[ChargeStatus]:
        return self.session.query(ChargeStatus).filter(ChargeStatus.enumerator == enumerator).first()

    def get_by_key(self, charge_key: str) -> Optional[Charge]:
        return self.session.query(Charge).filter(Charge.charge_key == charge_key).first()

    def create_charge(
        self,
        account_id: int,
        method_enum: str,
        amount: int,
        fee_amount: int,
        due_date: date,
        customer_document: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Charge:
        method = self.get_method(method_enum)
        status = self.get_status("created")
        charge_key = str(uuid4())

        charge = Charge()
        charge.charge_key = charge_key
        charge.account_id = account_id
        charge.method_id = method.id
        charge.status_id = status.id
        charge.amount = amount
        charge.fee_amount = fee_amount
        charge.net_amount = amount - fee_amount
        charge.due_date = due_date
        charge.customer_document = customer_document
        charge.charge_metadata = metadata

        if method_enum == "PIX":
            charge.qr_code = f"00020126580014br.gov.bcb.pix0136{charge_key}5204000053039865405{amount/100:.2f}5802BR5913QI_TECH6009SAO_PAULO62070503***6304"
        elif method_enum == "BOLETO":
            charge.barcode = f"341917900101043510047910201500098{amount:010d}"
        elif method_enum == "CREDIT_CARD_LINK":
            charge.payment_url = f"https://pay.qitech.com.br/c/{charge_key}"

        self.session.add(charge)
        self.session.commit()
        return charge

    def update_status(self, charge_id: int, to_status_enum: str, paid_at: Optional[datetime] = None) -> Charge:
        charge = self.session.query(Charge).filter(Charge.id == charge_id).first()
        status = self.get_status(to_status_enum)
        charge.status_id = status.id
        if paid_at:
            charge.paid_at = paid_at
        self.session.commit()
        return charge

    def create_webhook_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        signature: str,
    ) -> WebhookEvent:
        event = WebhookEvent()
        event.event_key = str(uuid4())
        event.event_type = event_type
        event.payload = payload
        event.signature = signature
        event.processed = False

        self.session.add(event)
        self.session.commit()
        return event

    def mark_webhook_processed(self, event_id: int) -> WebhookEvent:
        event = self.session.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
        event.processed = True
        event.processed_at = datetime.now()
        self.session.commit()
        return event

    def create_chargeback(self, charge_id: int, amount: int, reason: str) -> ChargebackClaim:
        claim = ChargebackClaim()
        claim.claim_key = str(uuid4())
        claim.charge_id = charge_id
        claim.amount = amount
        claim.reason = reason
        claim.status = "OPEN"

        self.session.add(claim)
        self.session.commit()
        return claim

    def get_pending_charges(self, charge_keys: Optional[list] = None, limit: int = 100) -> list:
        created_status = self.get_status("created")
        if not created_status:
            return []
        query = self.session.query(Charge).filter(Charge.status_id == created_status.id)
        if charge_keys:
            query = query.filter(Charge.charge_key.in_(charge_keys))
        return query.limit(limit).all()

