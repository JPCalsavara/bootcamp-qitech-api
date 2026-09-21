from models.ledger import LedgerEntry, Transaction


class TransactionDTO:
    @staticmethod
    def obj_to_dict(tx: Transaction) -> dict:
        return {
            "transaction_key": tx.transaction_key,
            "type": tx.transaction_type.enumerator if tx.transaction_type else None,
            "status": tx.status.enumerator if tx.status else None,
            "amount": tx.amount,
            "fee_amount": tx.fee_amount,
            "source_account_key": tx.source_account.account_key if tx.source_account else None,
            "destination_account_key": tx.destination_account.account_key if tx.destination_account else None,
            "description": tx.description,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
        }


class LedgerEntryDTO:
    @staticmethod
    def obj_to_dict(entry: LedgerEntry) -> dict:
        return {
            "entry_key": entry.entry_key,
            "entry_type": entry.entry_type,
            "amount": entry.amount,
            "balance_after": entry.balance_after,
            "description": entry.description,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
