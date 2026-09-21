from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from database import Context
from errors.custom_errors import InsufficientFunds
from models.pocket import Pocket, PocketType, RevenueTracker, TransferPolicy


class PocketRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_type(self, enumerator: str) -> Optional[PocketType]:
        return self.session.query(PocketType).filter(PocketType.enumerator == enumerator).first()

    def get_by_key(self, pocket_key: str) -> Optional[Pocket]:
        return self.session.query(Pocket).filter(Pocket.pocket_key == pocket_key).first()

    def get_pockets_by_account_id(self, account_id: int) -> List[Pocket]:
        return self.session.query(Pocket).filter(Pocket.account_id == account_id).all()

    def create_pocket(
        self,
        account_id: int,
        type_enum: str,
        name: str,
        target_amount: int = 0,
        is_locked: bool = False,
    ) -> Pocket:
        pocket_type = self.get_type(type_enum)
        pocket = Pocket()
        pocket.pocket_key = str(uuid4())
        pocket.account_id = account_id
        pocket.type_id = pocket_type.id
        pocket.name = name
        pocket.target_amount = target_amount
        pocket.current_balance = 0
        pocket.is_locked = is_locked

        self.session.add(pocket)
        self.session.commit()
        return pocket

    def update_pocket_balance(self, pocket_id: int, delta: int) -> Pocket:
        pocket = self.session.query(Pocket).filter(Pocket.id == pocket_id).with_for_update().first()
        if pocket.current_balance + delta < 0:
            raise InsufficientFunds("Saldo insuficiente na caixinha")
        pocket.current_balance += delta
        self.session.commit()
        return pocket

    def create_transfer_policy(
        self,
        account_pj_id: int,
        account_pf_id: int,
        max_daily_amount: int,
        require_pro_labore_approval: bool = True,
        das_reserved_check: bool = True,
    ) -> TransferPolicy:
        policy = TransferPolicy()
        policy.policy_key = str(uuid4())
        policy.account_pj_id = account_pj_id
        policy.account_pf_id = account_pf_id
        policy.max_daily_transfer_amount = max_daily_amount
        policy.require_pro_labore_approval = require_pro_labore_approval
        policy.das_reserved_check = das_reserved_check

        self.session.add(policy)
        self.session.commit()
        return policy

    def get_transfer_policy_by_pj(self, account_pj_id: int) -> Optional[TransferPolicy]:
        return self.session.query(TransferPolicy).filter(TransferPolicy.account_pj_id == account_pj_id).first()

    def get_or_create_revenue_tracker(self, customer_id: int, year: int) -> RevenueTracker:
        tracker = (
            self.session.query(RevenueTracker)
            .filter(
                RevenueTracker.customer_id == customer_id,
                RevenueTracker.calendar_year == year,
            )
            .first()
        )
        if not tracker:
            tracker = RevenueTracker()
            tracker.tracker_key = str(uuid4())
            tracker.customer_id = customer_id
            tracker.calendar_year = year
            tracker.accumulated_revenue = 0
            tracker.threshold_warning_sent = False
            tracker.threshold_danger_sent = False
            self.session.add(tracker)
            self.session.commit()
        return tracker

    def add_revenue(self, customer_id: int, year: int, amount: int) -> RevenueTracker:
        tracker = (
            self.session.query(RevenueTracker)
            .filter(
                RevenueTracker.customer_id == customer_id,
                RevenueTracker.calendar_year == year,
            )
            .with_for_update()
            .first()
        )
        if not tracker:
            tracker = self.get_or_create_revenue_tracker(customer_id, year)
            tracker = (
                self.session.query(RevenueTracker)
                .filter(RevenueTracker.id == tracker.id)
                .with_for_update()
                .first()
            )

        tracker.accumulated_revenue += amount
        # MEI limit = R$ 81.000,00 = 8.100.000 centavos
        # Warning: 80% = 6.480.000 centavos
        if tracker.accumulated_revenue >= 6_480_000:
            tracker.threshold_warning_sent = True
        if tracker.accumulated_revenue >= 8_100_000:
            tracker.threshold_danger_sent = True

        self.session.commit()
        return tracker
