from sqlalchemy import CHAR, BigInteger, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from models.base import Base
from models.customer import Customer
from models.account import Account
from models.pocket import Pocket


class CreditContractStatus(Base):
    __tablename__ = "credit_contract_status"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)


class CreditContract(Base):
    __tablename__ = "credit_contract"

    id = Column(Integer, primary_key=True)
    contract_key = Column(CHAR(36), nullable=False)
    customer_id = Column(Integer, ForeignKey(Customer.id), nullable=False)
    account_pj_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    account_pf_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    status_id = Column(Integer, ForeignKey(CreditContractStatus.id), nullable=False)
    requested_amount = Column(BigInteger, nullable=False)
    total_amount = Column(BigInteger, nullable=False)
    interest_rate_monthly = Column(Numeric(5, 4), nullable=False)
    term_months = Column(Integer, nullable=False)
    retention_percentage = Column(Numeric(5, 2), nullable=False)
    pocket_id = Column(Integer, ForeignKey(Pocket.id), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("contract_key"),)

    customer = relationship("Customer", foreign_keys=[customer_id], lazy="selectin")
    account_pj = relationship("Account", foreign_keys=[account_pj_id], lazy="selectin")
    account_pf = relationship("Account", foreign_keys=[account_pf_id], lazy="selectin")
    status = relationship("CreditContractStatus", foreign_keys=[status_id], lazy="selectin")
    pocket = relationship("Pocket", foreign_keys=[pocket_id], lazy="selectin")
    installments = relationship(
        "CreditInstallment",
        back_populates="contract",
        order_by="asc(CreditInstallment.installment_number)",
    )


class CreditInstallment(Base):
    __tablename__ = "credit_installment"

    id = Column(Integer, primary_key=True)
    installment_key = Column(CHAR(36), nullable=False)
    contract_id = Column(Integer, ForeignKey(CreditContract.id), nullable=False)
    installment_number = Column(Integer, nullable=False)
    amount = Column(BigInteger, nullable=False)
    principal_amount = Column(BigInteger, nullable=False)
    interest_amount = Column(BigInteger, nullable=False)
    due_date = Column(Date, nullable=False)
    paid_amount = Column(BigInteger, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="OPEN")
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("installment_key"),)

    contract = relationship("CreditContract", foreign_keys=[contract_id], back_populates="installments")


class ReceivablesAnticipation(Base):
    __tablename__ = "receivables_anticipation"

    id = Column(Integer, primary_key=True)
    anticipation_key = Column(CHAR(36), nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    original_amount = Column(BigInteger, nullable=False)
    discount_fee = Column(BigInteger, nullable=False)
    net_disbursed_amount = Column(BigInteger, nullable=False)
    charge_ids = Column(JSONB, nullable=False)
    status = Column(String(50), nullable=False, default="COMPLETED")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("anticipation_key"),)

    account = relationship("Account", foreign_keys=[account_id], lazy="selectin")
