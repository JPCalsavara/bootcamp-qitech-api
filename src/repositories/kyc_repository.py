from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from database import Context
from models.customer import Customer
from models.customer_status import CustomerStatus
from models.customer_status_event import CustomerStatusEvent
from models.kyc import KycAnalysis, KycRiskTier


class KycRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_risk_tier(self, enumerator: str) -> Optional[KycRiskTier]:
        return self.session.query(KycRiskTier).filter(KycRiskTier.enumerator == enumerator).first()

    def get_customer_status(self, enumerator: str) -> Optional[CustomerStatus]:
        return self.session.query(CustomerStatus).filter(CustomerStatus.enumerator == enumerator).first()

    def create_analysis(
        self,
        customer_id: int,
        risk_tier_enum: str,
        score: int,
        cnd_federal_status: str,
        cnd_trabalhista_status: str,
        cadsan_status: str,
        flags: Dict[str, Any],
        recommendation: str,
    ) -> KycAnalysis:
        tier = self.get_risk_tier(risk_tier_enum)
        analysis = KycAnalysis()
        analysis.analysis_key = str(uuid4())
        analysis.customer_id = customer_id
        analysis.risk_tier_id = tier.id
        analysis.score = score
        analysis.cnd_federal_status = cnd_federal_status
        analysis.cnd_trabalhista_status = cnd_trabalhista_status
        analysis.cadsan_status = cadsan_status
        analysis.flags = flags
        analysis.recommendation = recommendation

        self.session.add(analysis)
        self.session.flush()
        return analysis

    def transition_customer_status(
        self,
        customer_id: int,
        to_status_enum: str,
        reason_code: str,
        reason_detail: Optional[Dict[str, Any]] = None,
    ) -> Customer:
        customer = self.session.query(Customer).filter(Customer.id == customer_id).first()
        to_status = self.get_customer_status(to_status_enum)
        from_id = customer.status_id
        customer.status_id = to_status.id
        self.session.flush()

        event = CustomerStatusEvent()
        event.customer_id = customer.id
        event.from_status_id = from_id
        event.to_status_id = to_status.id
        event.reason_code = reason_code
        event.reason_detail = reason_detail or {}
        event.event_datetime = datetime.now()

        self.session.add(event)
        self.session.commit()
        return customer
