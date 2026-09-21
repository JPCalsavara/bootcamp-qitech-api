from datetime import datetime
from typing import List

from controllers.base_controller import BaseController
from dtos.pocket_dto import PocketDTO, RevenueTrackerDTO, TransferPolicyDTO
from errors.custom_errors import InsufficientFunds, NotFoundAccount, NotFoundCustomer
from repositories.account_repository import AccountRepository
from repositories.customer_repository import CustomerRepository
from repositories.pocket_repository import PocketRepository


class PocketController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.pocket_repository = PocketRepository(self.context)
        self.account_repository = AccountRepository(self.context)
        self.customer_repository = CustomerRepository(self.context)

    def create_pocket(self, account_key: str, payload: dict) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)

        pocket = self.pocket_repository.create_pocket(
            account_id=account.id,
            type_enum=payload["type"],
            name=payload["name"],
            target_amount=payload.get("target_amount", 0),
            is_locked=payload.get("is_locked", False),
        )
        return PocketDTO.obj_to_dict(pocket)

    def get_pockets(self, account_key: str) -> List[dict]:
        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)

        pockets = self.pocket_repository.get_pockets_by_account_id(account.id)
        return [PocketDTO.obj_to_dict(p) for p in pockets]

    def create_transfer_policy(self, payload: dict) -> dict:
        pj_key = payload["account_pj_key"]
        pf_key = payload["account_pf_key"]
        max_amount = payload["max_daily_transfer_amount"]
        require_approval = payload.get("require_pro_labore_approval", True)
        das_check = payload.get("das_reserved_check", True)

        account_pj = self.account_repository.get_by_key(pj_key)
        if not account_pj:
            raise NotFoundAccount(pj_key)

        account_pf = self.account_repository.get_by_key(pf_key)
        if not account_pf:
            raise NotFoundAccount(pf_key)

        policy = self.pocket_repository.create_transfer_policy(
            account_pj_id=account_pj.id,
            account_pf_id=account_pf.id,
            max_daily_amount=max_amount,
            require_pro_labore_approval=require_approval,
            das_reserved_check=das_check,
        )
        return TransferPolicyDTO.obj_to_dict(policy)

    def get_revenue_tracker(self, customer_key: str) -> dict:
        customer = self.customer_repository.get_by_key(customer_key)
        if not customer:
            raise NotFoundCustomer(customer_key)

        tracker = self.pocket_repository.get_or_create_revenue_tracker(
            customer_id=customer.id,
            year=datetime.now().year,
        )
        return RevenueTrackerDTO.obj_to_dict(tracker)

    def deposit_to_pocket(self, account_key: str, pocket_key: str, payload: dict) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)
        pocket = self.pocket_repository.get_by_key(pocket_key)
        if not pocket:
            raise NotFoundAccount(pocket_key)
        amount = payload["amount"]
        if account.balance < amount:
            raise InsufficientFunds("Saldo insuficiente para depositar na caixinha")
        account.balance -= amount
        pocket = self.pocket_repository.update_pocket_balance(pocket.id, amount)
        return PocketDTO.obj_to_dict(pocket)

