from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from database import Context
from models.account import Account
from models.yield_position import YieldAccrualEvent, YieldPosition


class YieldRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_or_create_position(self, account_id: int) -> YieldPosition:
        pos = self.session.query(YieldPosition).filter(YieldPosition.account_id == account_id).first()
        if not pos:
            pos = YieldPosition()
            pos.position_key = str(uuid4())
            pos.account_id = account_id
            pos.principal_amount = 0
            pos.accumulated_yield = 0
            pos.iof_amount = 0
            pos.ir_amount = 0
            pos.net_yield = 0
            self.session.add(pos)
            self.session.commit()
        return pos

    def accrue_daily_yield(
        self,
        account: Account,
        cdi_daily_rate: Decimal = Decimal("0.00045"),
    ) -> YieldAccrualEvent:
        pos = self.get_or_create_position(account.id)

        # Rendimento diário sobre o saldo positivo
        principal = max(0, account.balance)
        gross_yield = int(Decimal(principal) * cdi_daily_rate)

        # IR de 22,5% (alíquota inicial < 180 dias)
        ir_withheld = int(Decimal(gross_yield) * Decimal("0.225"))
        iof_withheld = 0
        net_yield = gross_yield - ir_withheld - iof_withheld

        pos.principal_amount = principal
        pos.accumulated_yield += gross_yield
        pos.ir_amount += ir_withheld
        pos.iof_amount += iof_withheld
        pos.net_yield += net_yield
        pos.last_accrual_date = date.today()

        event = YieldAccrualEvent()
        event.event_key = str(uuid4())
        event.position_id = pos.id
        event.date = date.today()
        event.cdi_daily_rate = cdi_daily_rate
        event.gross_yield = gross_yield
        event.iof_withheld = iof_withheld
        event.ir_withheld = ir_withheld
        event.net_yield = net_yield

        self.session.add(event)
        self.session.commit()
        return event
