from decimal import Decimal

from controllers.base_controller import BaseController
from dtos.yield_dto import YieldAccrualEventDTO, YieldPositionDTO
from errors.custom_errors import InsufficientFunds, NotFoundAccount
from models.account import Account
from repositories.account_repository import AccountRepository
from repositories.ledger_repository import LedgerRepository
from repositories.yield_repository import YieldRepository


class YieldController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.yield_repository = YieldRepository(self.context)
        self.account_repository = AccountRepository(self.context)
        self.ledger_repository = LedgerRepository(self.context)

    def accrue_yield(self, payload: dict) -> dict:
        account_key = payload["account_key"]
        rate = Decimal(str(payload.get("cdi_daily_rate", "0.00045")))

        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)

        event = self.yield_repository.accrue_daily_yield(account=account, cdi_daily_rate=rate)

        # Se houve rendimento líquido, credita na conta com tipo TREASURY_YIELD
        if event.net_yield > 0:
            self.ledger_repository.execute_cash_in(
                dest_account=account,
                amount=event.net_yield,
                type_enum="TREASURY_YIELD",
                description="Rendimento Automático CDB 100% CDI",
            )

        pos = self.yield_repository.get_or_create_position(account.id)

        return {
            "accrual_event": YieldAccrualEventDTO.obj_to_dict(event),
            "position": YieldPositionDTO.obj_to_dict(pos),
        }

    def get_position(self, account_key: str) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)

        pos = self.yield_repository.get_or_create_position(account.id)
        return YieldPositionDTO.obj_to_dict(pos)

    def invest(self, payload: dict) -> dict:
        account_key = payload["account_key"]
        amount = payload["amount"]

        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)

        acc = self.context.db_session.query(Account).filter(Account.id == account.id).with_for_update().first()
        blocked = getattr(acc, "blocked_balance", 0) or 0
        if (acc.balance - blocked) < amount:
            raise InsufficientFunds("Saldo disponível insuficiente para aplicação em CDB")

        acc.balance -= amount
        pos = self.yield_repository.add_to_position(account.id, amount)

        tx = self.ledger_repository.create_transaction(
            type_enum="TREASURY_YIELD",
            amount=amount,
            source_account_id=acc.id,
            description="Aplicação em CDB 100% CDI",
        )
        self.ledger_repository.create_ledger_entry(
            transaction_id=tx.id,
            account_id=acc.id,
            entry_type="DEBIT",
            amount=amount,
            balance_after=acc.balance,
            description="Aplicação em CDB 100% CDI",
        )
        self.ledger_repository.update_transaction_status(tx.id, "completed", "CDB_INVESTMENT_SETTLED")
        self.context.db_session.commit()

        return YieldPositionDTO.obj_to_dict(pos)

