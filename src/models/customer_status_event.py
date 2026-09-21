from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from models.base import Base
from models.customer_status import CustomerStatus


class CustomerStatusEvent(Base):
    __tablename__ = "customer_status_event"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    from_status_id = Column(Integer, ForeignKey(CustomerStatus.id), nullable=True)
    to_status_id = Column(Integer, ForeignKey(CustomerStatus.id), nullable=False)
    reason_code = Column(String(100), nullable=False)
    reason_detail = Column(JSONB, nullable=True)
    event_datetime = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    customer = relationship("Customer", back_populates="status_events")
    from_status = relationship("CustomerStatus", foreign_keys=[from_status_id], lazy="selectin")
    to_status = relationship("CustomerStatus", foreign_keys=[to_status_id], lazy="selectin")
