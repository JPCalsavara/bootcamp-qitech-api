from models.pocket import Pocket, RevenueTracker, TransferPolicy


class PocketDTO:
    @staticmethod
    def obj_to_dict(pocket: Pocket) -> dict:
        return {
            "pocket_key": pocket.pocket_key,
            "type": pocket.pocket_type.enumerator if pocket.pocket_type else None,
            "name": pocket.name,
            "target_amount": pocket.target_amount,
            "current_balance": pocket.current_balance,
            "is_locked": pocket.is_locked,
            "created_at": pocket.created_at.isoformat() if pocket.created_at else None,
        }


class TransferPolicyDTO:
    @staticmethod
    def obj_to_dict(policy: TransferPolicy) -> dict:
        return {
            "policy_key": policy.policy_key,
            "account_pj_key": policy.account_pj.account_key if policy.account_pj else None,
            "account_pf_key": policy.account_pf.account_key if policy.account_pf else None,
            "max_daily_transfer_amount": policy.max_daily_transfer_amount,
            "require_pro_labore_approval": policy.require_pro_labore_approval,
            "das_reserved_check": policy.das_reserved_check,
        }


class RevenueTrackerDTO:
    @staticmethod
    def obj_to_dict(tracker: RevenueTracker) -> dict:
        return {
            "tracker_key": tracker.tracker_key,
            "calendar_year": tracker.calendar_year,
            "accumulated_revenue": tracker.accumulated_revenue,
            "annual_limit": 8_100_000,  # R$ 81.000,00 em centavos
            "threshold_warning_sent": tracker.threshold_warning_sent,
            "threshold_danger_sent": tracker.threshold_danger_sent,
        }
