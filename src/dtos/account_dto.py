from models.account import Account


class AccountDTO:
    @staticmethod
    def obj_to_dict(account: Account) -> dict:
        blocked = getattr(account, "blocked_balance", 0) or 0
        return {
            "account_key": account.account_key,
            "type": account.account_type.enumerator if account.account_type else None,
            "status": account.status.enumerator if account.status else None,
            "branch_number": account.branch_number,
            "account_number": account.account_number,
            "balance": account.balance,
            "blocked_balance": blocked,
            "available_balance": account.balance - blocked,
            "created_at": account.created_at.isoformat() if account.created_at else None,
        }

