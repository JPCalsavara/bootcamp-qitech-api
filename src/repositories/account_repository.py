import random
from typing import List, Optional
from uuid import uuid4
from database import Context
from models.account import Account, AccountStatus, AccountStatusEvent, AccountType


class AccountRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_type(self, enumerator: str) -> Optional[AccountType]:
        return self.session.query(AccountType).filter(AccountType.enumerator == enumerator).first()

    def get_status(self, enumerator: str) -> Optional[AccountStatus]:
        return self.session.query(AccountStatus).filter(AccountStatus.enumerator == enumerator).first()

    def get_by_key(self, account_key: str) -> Optional[Account]:
        return self.session.query(Account).filter(Account.account_key == account_key).first()

    def get_by_id(self, account_id: int) -> Optional[Account]:
        return self.session.query(Account).filter(Account.id == account_id).first()

    def get_by_customer_id(self, customer_id: int) -> List[Account]:
        return self.session.query(Account).filter(Account.customer_id == customer_id).all()

    def create(self, customer_id: int, type_enum: str, branch_number: str = "0001") -> Account:
        acc_type = self.get_type(type_enum)
        acc_status = self.get_status("active")
        account = Account()
        account.account_key = str(uuid4())
        account.customer_id = customer_id
        account.type_id = acc_type.id
        account.status_id = acc_status.id
        account.branch_number = branch_number
        # Gera número de conta no formato XXXXXX-X
        account.account_number = f"{random.randint(100000, 999999)}-{random.randint(0, 9)}"
        account.balance = 0
        self.session.add(account)
        self.session.flush()

        event = AccountStatusEvent()
        event.account_id = account.id
        event.from_status_id = None
        event.to_status_id = acc_status.id
        event.reason_code = "ACCOUNT_OPENED"
        self.session.add(event)
        self.session.commit()
        return account

    def create_twin_accounts(self, customer_id: int) -> List[Account]:
        """Cria as duas contas vinculadas: PJ (MEI) e PF (titular)."""
        existing = self.get_by_customer_id(customer_id)
        if existing:
            return existing
        pf_account = self.create(customer_id, "PF")
        pj_account = self.create(customer_id, "PJ")
        return [pf_account, pj_account]

    def lock_accounts_ordered(self, account_ids: List[int]) -> List[Account]:
        """ADR-0002: Dijkstra Lock Ordering - ordena IDs crescentemente e adquire SELECT ... FOR UPDATE."""
        sorted_ids = sorted(list(set(account_ids)))
        locked_accounts = []
        for aid in sorted_ids:
            acc = self.session.query(Account).filter(Account.id == aid).with_for_update().first()
            if acc:
                locked_accounts.append(acc)
        return locked_accounts

    def update_balance(self, account_id: int, new_balance: int) -> Account:
        account = self.get_by_id(account_id)
        account.balance = new_balance
        self.session.flush()
        return account

    def update_status(self, account_id: int, to_status_enum: str, reason_code: str) -> Account:
        account = self.get_by_id(account_id)
        from_status_id = account.status_id
        to_status = self.get_status(to_status_enum)
        account.status_id = to_status.id

        event = AccountStatusEvent()
        event.account_id = account.id
        event.from_status_id = from_status_id
        event.to_status_id = to_status.id
        event.reason_code = reason_code
        self.session.add(event)
        self.session.commit()
        return account

    def update_blocked_balance(self, account_id: int, new_blocked_balance: int) -> Account:
        account = self.get_by_id(account_id)
        account.blocked_balance = new_blocked_balance
        self.session.commit()
        return account

