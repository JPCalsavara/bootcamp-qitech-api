from models.yield_position import YieldAccrualEvent, YieldPosition


class YieldPositionDTO:
    @staticmethod
    def obj_to_dict(pos: YieldPosition) -> dict:
        return {
            "position_key": pos.position_key,
            "account_key": pos.account.account_key if pos.account else None,
            "principal_amount": pos.principal_amount,
            "accumulated_yield": pos.accumulated_yield,
            "iof_amount": pos.iof_amount,
            "ir_amount": pos.ir_amount,
            "net_yield": pos.net_yield,
            "last_accrual_date": pos.last_accrual_date.isoformat() if pos.last_accrual_date else None,
            "created_at": pos.created_at.isoformat() if pos.created_at else None,
        }


class YieldAccrualEventDTO:
    @staticmethod
    def obj_to_dict(event: YieldAccrualEvent) -> dict:
        return {
            "event_key": event.event_key,
            "date": event.date.isoformat() if event.date else None,
            "cdi_daily_rate": float(event.cdi_daily_rate),
            "gross_yield": event.gross_yield,
            "iof_withheld": event.iof_withheld,
            "ir_withheld": event.ir_withheld,
            "net_yield": event.net_yield,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
