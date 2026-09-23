from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from database import Context
from errors.custom_errors import InsufficientFunds
from models.account import Account
from models.ledger import (
    IdempotencyRecord,
    LedgerEntry,
    Transaction,
    TransactionStatus,
    TransactionStatusEvent,
    TransactionType,
)
from models.yield_position import YieldPosition


class LedgerRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_type(self, enumerator: str) -> Optional[TransactionType]:
        return self.session.query(TransactionType).filter(TransactionType.enumerator == enumerator).first()

    def get_status(self, enumerator: str) -> Optional[TransactionStatus]:
        return self.session.query(TransactionStatus).filter(TransactionStatus.enumerator == enumerator).first()

    def get_idempotency(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        return (
            self.session.query(IdempotencyRecord)
            .filter(
                IdempotencyRecord.idempotency_key == idempotency_key,
                IdempotencyRecord.expires_at > datetime.now(),
            )
            .first()
        )

    def save_idempotency(
        self,
        idempotency_key: str,
        request_hash: str,
        response_code: int,
        response_body: Dict[str, Any],
        ttl_seconds: int = 86400,
    ) -> IdempotencyRecord:
        record = IdempotencyRecord()
        record.idempotency_key = idempotency_key
        record.request_hash = request_hash
        record.response_code = response_code
        record.response_body = response_body
        record.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        self.session.add(record)
        self.session.commit()
        return record


    def create_transaction(
        self,
        type_enum: str,
        amount: int,
        fee_amount: int = 0,
        source_account_id: Optional[int] = None,
        destination_account_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Transaction:
        tx_type = self.get_type(type_enum)
        tx_status = self.get_status("pending")

        tx = Transaction()
        tx.transaction_key = str(uuid4())
        tx.idempotency_key = idempotency_key
        tx.type_id = tx_type.id
        tx.status_id = tx_status.id
        tx.amount = amount
        tx.fee_amount = fee_amount
        tx.source_account_id = source_account_id
        tx.destination_account_id = destination_account_id
        tx.description = description
        tx.tx_metadata = metadata

        self.session.add(tx)
        self.session.flush()
        return tx

    def create_ledger_entry(
        self,
        transaction_id: int,
        account_id: int,
        entry_type: str,
        amount: int,
        balance_after: int,
        description: Optional[str] = None,
    ) -> LedgerEntry:
        entry = LedgerEntry()
        entry.entry_key = str(uuid4())
        entry.transaction_id = transaction_id
        entry.account_id = account_id
        entry.entry_type = entry_type
        entry.amount = amount
        entry.balance_after = balance_after
        entry.description = description

        self.session.add(entry)
        self.session.flush()
        return entry

    def update_transaction_status(self, transaction_id: int, to_status_enum: str, reason: str) -> Transaction:
        status = self.get_status(to_status_enum)
        tx = self.session.query(Transaction).filter(Transaction.id == transaction_id).first()
        from_id = tx.status_id
        tx.status_id = status.id
        self.session.flush()

        event = TransactionStatusEvent()
        event.transaction_id = tx.id
        event.from_status_id = from_id
        event.to_status_id = status.id
        event.reason_code = reason
        self.session.add(event)
        self.session.flush()
        return tx

    def get_entries_by_account_id(self, account_id: int, limit: int = 50, offset: int = 0) -> List[LedgerEntry]:
        return (
            self.session.query(LedgerEntry)
            .filter(LedgerEntry.account_id == account_id)
            .order_by(LedgerEntry.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def execute_transfer(
        self,
        source_account: Account,
        dest_account: Account,
        amount: int,
        type_enum: str = "TRANSFER_INTERNAL",
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Transaction:
        """Executa transferência com trava Dijkstra e double-entry ledger atômico."""
        # Dijkstra Lock: menor ID primeiro
        first_id, second_id = (
            (source_account.id, dest_account.id)
            if source_account.id < dest_account.id
            else (dest_account.id, source_account.id)
        )

        acc_first = self.session.query(Account).filter(Account.id == first_id).with_for_update().first()
        acc_second = self.session.query(Account).filter(Account.id == second_id).with_for_update().first()

        src = acc_first if acc_first.id == source_account.id else acc_second
        dst = acc_first if acc_first.id == dest_account.id else acc_second

        blocked = getattr(src, "blocked_balance", 0) or 0
        available = src.balance - blocked
        if available < amount:
            deficit = amount - available
            yield_pos = (
                self.session.query(YieldPosition)
                .filter(YieldPosition.account_id == src.id)
                .with_for_update()
                .first()
            )
            if yield_pos and yield_pos.principal_amount >= deficit:
                # Cash Sweep automático e atômico de CDB (RFC 03)
                yield_pos.principal_amount -= deficit
                src.balance += deficit

                sweep_tx = self.create_transaction(
                    type_enum="TREASURY_YIELD",
                    amount=deficit,
                    destination_account_id=src.id,
                    description="Resgate Automático Cash Sweep CDB",
                )
                self.create_ledger_entry(
                    transaction_id=sweep_tx.id,
                    account_id=src.id,
                    entry_type="CREDIT",
                    amount=deficit,
                    balance_after=src.balance,
                    description="Resgate Automático Cash Sweep CDB",
                )
                self.update_transaction_status(sweep_tx.id, "completed", "CASH_SWEEP_EXECUTED")
            else:
                raise InsufficientFunds("Saldo disponível insuficiente para transferência")



        tx = self.create_transaction(
            type_enum=type_enum,
            amount=amount,
            source_account_id=src.id,
            destination_account_id=dst.id,
            idempotency_key=idempotency_key,
            description=description,
        )

        # Atualiza saldos
        src.balance -= amount
        dst.balance += amount

        # Grava partidas dobradas no Ledger
        self.create_ledger_entry(
            transaction_id=tx.id,
            account_id=src.id,
            entry_type="DEBIT",
            amount=amount,
            balance_after=src.balance,
            description=f"Transferência enviada: {description or ''}".strip(),
        )

        self.create_ledger_entry(
            transaction_id=tx.id,
            account_id=dst.id,
            entry_type="CREDIT",
            amount=amount,
            balance_after=dst.balance,
            description=f"Transferência recebida: {description or ''}".strip(),
        )

        self.update_transaction_status(tx.id, "completed", "TRANSFER_EXECUTED")
        self.session.commit()
        return tx

    def execute_cash_in(
        self,
        dest_account: Account,
        amount: int,
        fee_amount: int = 0,
        type_enum: str = "PIX_CASH_IN",
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Transaction:
        """ADR-0008: Liquidação bruta + débito atômico de tarifa."""
        acc = self.session.query(Account).filter(Account.id == dest_account.id).with_for_update().first()

        tx = self.create_transaction(
            type_enum=type_enum,
            amount=amount,
            fee_amount=fee_amount,
            destination_account_id=acc.id,
            idempotency_key=idempotency_key,
            description=description,
            metadata=metadata,
        )

        # 1. Crédito bruto
        acc.balance += amount
        self.create_ledger_entry(
            transaction_id=tx.id,
            account_id=acc.id,
            entry_type="CREDIT",
            amount=amount,
            balance_after=acc.balance,
            description=f"Cash-in bruto: {description or ''}".strip(),
        )

        # 2. Débito atômico da taxa (se houver)
        if fee_amount > 0:
            acc.balance -= fee_amount
            self.create_ledger_entry(
                transaction_id=tx.id,
                account_id=acc.id,
                entry_type="DEBIT",
                amount=fee_amount,
                balance_after=acc.balance,
                description=f"Tarifa transacional {type_enum}",
            )

        self.update_transaction_status(tx.id, "completed", "CASH_IN_SETTLED")
        self.session.commit()
        return tx
