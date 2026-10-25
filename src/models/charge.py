from sqlalchemy import CHAR, BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from models.base import Base
from models.account import Account


class ChargeMethod(Base):
    __tablename__ = "charge_method"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)


class ChargeStatus(Base):
    __tablename__ = "charge_status"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)


class Charge(Base):
    __tablename__ = "charge"

    id = Column(Integer, primary_key=True)
    charge_key = Column(CHAR(36), nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    method_id = Column(Integer, ForeignKey(ChargeMethod.id), nullable=False)
    status_id = Column(Integer, ForeignKey(ChargeStatus.id), nullable=False)
    amount = Column(BigInteger, nullable=False)
    fee_amount = Column(BigInteger, nullable=False, default=0)
    net_amount = Column(BigInteger, nullable=False)
    due_date = Column(Date, nullable=False)
    qr_code = Column(Text, nullable=True)
    barcode = Column(String(100), nullable=True)
    payment_url = Column(Text, nullable=True)
    customer_document = Column(String(20), nullable=True)
    charge_metadata = Column("metadata", JSONB, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("charge_key"),)

    account = relationship("Account", foreign_keys=[account_id], lazy="selectin")
    method = relationship("ChargeMethod", foreign_keys=[method_id], lazy="selectin")
    status = relationship("ChargeStatus", foreign_keys=[status_id], lazy="selectin")


class WebhookEventType(Base):
    __tablename__ = "webhook_event_type"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)


class WebhookEvent(Base):
    __tablename__ = "webhook_event"

    id = Column(Integer, primary_key=True)
    event_key = Column(CHAR(36), nullable=False)
    event_type_id = Column(Integer, ForeignKey(WebhookEventType.id), nullable=False)
    payload = Column(JSONB, nullable=False)
    signature = Column(String(255), nullable=False)
    processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("event_key"),)

    event_type = relationship("WebhookEventType", foreign_keys=[event_type_id], lazy="selectin")


class ChargebackClaimStatus(Base):
    __tablename__ = "chargeback_claim_status"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)


class ChargebackClaim(Base):
    __tablename__ = "chargeback_claim"

    id = Column(Integer, primary_key=True)
    claim_key = Column(CHAR(36), nullable=False)
    charge_id = Column(Integer, ForeignKey(Charge.id), nullable=False)
    amount = Column(BigInteger, nullable=False)
    reason = Column(String(255), nullable=False)
    status_id = Column(Integer, ForeignKey(ChargebackClaimStatus.id), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("claim_key"),)

    charge = relationship("Charge", foreign_keys=[charge_id], lazy="selectin")
    status = relationship("ChargebackClaimStatus", foreign_keys=[status_id], lazy="selectin")


class ChargeStatusEvent(Base):
    __tablename__ = "charge_status_event"

    id = Column(Integer, primary_key=True)
    charge_id = Column(Integer, ForeignKey(Charge.id), nullable=False)
    from_status_id = Column(Integer, ForeignKey(ChargeStatus.id), nullable=True)
    to_status_id = Column(Integer, ForeignKey(ChargeStatus.id), nullable=False)
    reason_code = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    charge = relationship("Charge", foreign_keys=[charge_id])
    to_status = relationship("ChargeStatus", foreign_keys=[to_status_id], lazy="selectin")


class ChargebackClaimStatusEvent(Base):
    __tablename__ = "chargeback_claim_status_event"

    id = Column(Integer, primary_key=True)
    chargeback_claim_id = Column(Integer, ForeignKey(ChargebackClaim.id), nullable=False)
    from_status_id = Column(Integer, ForeignKey(ChargebackClaimStatus.id), nullable=True)
    to_status_id = Column(Integer, ForeignKey(ChargebackClaimStatus.id), nullable=False)
    reason_code = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    chargeback_claim = relationship("ChargebackClaim", foreign_keys=[chargeback_claim_id])
    to_status = relationship("ChargebackClaimStatus", foreign_keys=[to_status_id], lazy="selectin")
