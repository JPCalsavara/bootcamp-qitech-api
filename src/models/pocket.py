from sqlalchemy import CHAR, BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models.account import Account
from models.customer import Customer


class PocketType(Base):
    __tablename__ = "pocket_type"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)


class Pocket(Base):
    __tablename__ = "pocket"

    id = Column(Integer, primary_key=True)
    pocket_key = Column(CHAR(36), nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    type_id = Column(Integer, ForeignKey(PocketType.id), nullable=False)
    name = Column(String(100), nullable=False)
    target_amount = Column(BigInteger, nullable=False, default=0)
    current_balance = Column(BigInteger, nullable=False, default=0)
    is_locked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("pocket_key"),)

    account = relationship("Account", foreign_keys=[account_id], lazy="selectin")
    pocket_type = relationship("PocketType", foreign_keys=[type_id], lazy="selectin")


class TransferPolicy(Base):
    __tablename__ = "transfer_policy"

    id = Column(Integer, primary_key=True)
    policy_key = Column(CHAR(36), nullable=False)
    account_pj_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    account_pf_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    max_daily_transfer_amount = Column(BigInteger, nullable=False)
    require_pro_labore_approval = Column(Boolean, nullable=False, default=True)
    das_reserved_check = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("policy_key"),)

    account_pj = relationship("Account", foreign_keys=[account_pj_id], lazy="selectin")
    account_pf = relationship("Account", foreign_keys=[account_pf_id], lazy="selectin")


class RevenueTracker(Base):
    __tablename__ = "revenue_tracker"

    id = Column(Integer, primary_key=True)
    tracker_key = Column(CHAR(36), nullable=False)
    customer_id = Column(Integer, ForeignKey(Customer.id), nullable=False)
    calendar_year = Column(Integer, nullable=False)
    accumulated_revenue = Column(BigInteger, nullable=False, default=0)
    threshold_warning_sent = Column(Boolean, nullable=False, default=False)
    threshold_danger_sent = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tracker_key"),
        UniqueConstraint("customer_id", "calendar_year"),
    )

    customer = relationship("Customer", foreign_keys=[customer_id], lazy="selectin")
