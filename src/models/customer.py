from sqlalchemy import CHAR, Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models.customer_status import CustomerStatus


class Customer(Base):
    __tablename__ = "customer"

    id = Column(Integer, primary_key=True)
    customer_key = Column(CHAR(36), nullable=False)
    status_id = Column(Integer, ForeignKey(CustomerStatus.id), nullable=False)
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    cpf = Column(CHAR(14), nullable=False)
    cnpj = Column(CHAR(18), nullable=False)
    birthdate = Column(Date, nullable=False)
    phone = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    pin_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("customer_key"),
        UniqueConstraint("email"),
        UniqueConstraint("cpf"),
        UniqueConstraint("cnpj"),
    )

    status = relationship("CustomerStatus", foreign_keys=[status_id], lazy="selectin")
    status_events = relationship(
        "CustomerStatusEvent",
        back_populates="customer",
        order_by="asc(CustomerStatusEvent.event_datetime)",
    )
