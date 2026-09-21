from models.charge import Charge


class ChargeDTO:
    @staticmethod
    def obj_to_dict(charge: Charge) -> dict:
        return {
            "charge_key": charge.charge_key,
            "account_key": charge.account.account_key if charge.account else None,
            "method": charge.method.enumerator if charge.method else None,
            "status": charge.status.enumerator if charge.status else None,
            "amount": charge.amount,
            "fee_amount": charge.fee_amount,
            "net_amount": charge.net_amount,
            "due_date": charge.due_date.isoformat() if charge.due_date else None,
            "qr_code": charge.qr_code,
            "barcode": charge.barcode,
            "payment_url": charge.payment_url,
            "paid_at": charge.paid_at.isoformat() if charge.paid_at else None,
            "created_at": charge.created_at.isoformat() if charge.created_at else None,
        }
