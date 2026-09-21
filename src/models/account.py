from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models.customer import Customer


class AccountType(Base):
    __tablename__ = "account_type"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)


class AccountStatus(Base):
    __tablename__ = "account_status"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)


class Account(Base):
    __tablename__ = "account"

    id = Column(Integer, primary_key=True)
    account_key = Column(CHAR(36), nullable=False)
    customer_id = Column(Integer, ForeignKey(Customer.id), nullable=False)
    type_id = Column(Integer, ForeignKey(AccountType.id), nullable=False)
    status_id = Column(Integer, ForeignKey(AccountStatus.id), nullable=False)
    branch_number = Column(String(10), nullable=False, default="0001")
    account_number = Column(String(20), nullable=False)
    balance = Column(Integer, nullable=False, default=0)
    blocked_balance = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("account_key"),
        UniqueConstraint("account_number"),
        UniqueConstraint("customer_id", "type_id"),
    )

    customer = relationship("Customer", foreign_keys=[customer_id], lazy="selectin")
    account_type = relationship("AccountType", foreign_keys=[type_id], lazy="selectin")
    status = relationship("AccountStatus", foreign_keys=[status_id], lazy="selectin")


class AccountStatusEvent(Base):
    __tablename__ = "account_status_event"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    from_status_id = Column(Integer, ForeignKey(AccountStatus.id), nullable=True)
    to_status_id = Column(Integer, ForeignKey(AccountStatus.id), nullable=False)
    reason_code = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    account = relationship("Account", foreign_keys=[account_id])
    to_status = relationship("AccountStatus", foreign_keys=[to_status_id], lazy="selectin")
