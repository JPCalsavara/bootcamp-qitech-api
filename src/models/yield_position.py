from sqlalchemy import CHAR, BigInteger, Column, Date, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models.account import Account


class YieldPosition(Base):
    __tablename__ = "yield_position"

    id = Column(Integer, primary_key=True)
    position_key = Column(CHAR(36), nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    principal_amount = Column(BigInteger, nullable=False, default=0)
    accumulated_yield = Column(BigInteger, nullable=False, default=0)
    iof_amount = Column(BigInteger, nullable=False, default=0)
    ir_amount = Column(BigInteger, nullable=False, default=0)
    net_yield = Column(BigInteger, nullable=False, default=0)
    last_accrual_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("position_key"),
        UniqueConstraint("account_id"),
    )

    account = relationship("Account", foreign_keys=[account_id], lazy="selectin")
    events = relationship("YieldAccrualEvent", back_populates="position")


class YieldAccrualEvent(Base):
    __tablename__ = "yield_accrual_event"

    id = Column(Integer, primary_key=True)
    event_key = Column(CHAR(36), nullable=False)
    position_id = Column(Integer, ForeignKey(YieldPosition.id), nullable=False)
    date = Column(Date, nullable=False)
    cdi_daily_rate = Column(Numeric(8, 6), nullable=False)
    gross_yield = Column(BigInteger, nullable=False)
    iof_withheld = Column(BigInteger, nullable=False)
    ir_withheld = Column(BigInteger, nullable=False)
    net_yield = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("event_key"),)

    position = relationship("YieldPosition", foreign_keys=[position_id], back_populates="events")
