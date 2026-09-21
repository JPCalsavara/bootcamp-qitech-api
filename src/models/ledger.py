from sqlalchemy import CHAR, BigInteger, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from models.base import Base
from models.account import Account


class TransactionType(Base):
    __tablename__ = "transaction_type"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)


class TransactionStatus(Base):
    __tablename__ = "transaction_status"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)


class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(Integer, primary_key=True)
    transaction_key = Column(CHAR(36), nullable=False)
    idempotency_key = Column(String(255), nullable=True)
    type_id = Column(Integer, ForeignKey(TransactionType.id), nullable=False)
    status_id = Column(Integer, ForeignKey(TransactionStatus.id), nullable=False)
    amount = Column(BigInteger, nullable=False)
    fee_amount = Column(BigInteger, nullable=False, default=0)
    source_account_id = Column(Integer, ForeignKey(Account.id), nullable=True)
    destination_account_id = Column(Integer, ForeignKey(Account.id), nullable=True)
    description = Column(String(255), nullable=True)
    tx_metadata = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("transaction_key"),
        UniqueConstraint("idempotency_key"),
    )

    transaction_type = relationship("TransactionType", foreign_keys=[type_id], lazy="selectin")
    status = relationship("TransactionStatus", foreign_keys=[status_id], lazy="selectin")
    source_account = relationship("Account", foreign_keys=[source_account_id], lazy="selectin")
    destination_account = relationship("Account", foreign_keys=[destination_account_id], lazy="selectin")


class TransactionStatusEvent(Base):
    __tablename__ = "transaction_status_event"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey(Transaction.id), nullable=False)
    from_status_id = Column(Integer, ForeignKey(TransactionStatus.id), nullable=True)
    to_status_id = Column(Integer, ForeignKey(TransactionStatus.id), nullable=False)
    reason_code = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    to_status = relationship("TransactionStatus", foreign_keys=[to_status_id], lazy="selectin")


class LedgerEntry(Base):
    __tablename__ = "ledger_entry"

    id = Column(Integer, primary_key=True)
    entry_key = Column(CHAR(36), nullable=False)
    transaction_id = Column(Integer, ForeignKey(Transaction.id), nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    entry_type = Column(String(10), nullable=False)
    amount = Column(BigInteger, nullable=False)
    balance_after = Column(BigInteger, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("entry_key"),)

    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    account = relationship("Account", foreign_keys=[account_id])


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_record"

    id = Column(Integer, primary_key=True)
    idempotency_key = Column(String(255), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_code = Column(Integer, nullable=False)
    response_body = Column(JSONB, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("idempotency_key"),)
