from models.credit import CreditContract, CreditInstallment, ReceivablesAnticipation


class CreditContractDTO:
    @staticmethod
    def obj_to_dict(contract: CreditContract) -> dict:
        return {
            "contract_key": contract.contract_key,
            "customer_key": contract.customer.customer_key if contract.customer else None,
            "account_pj_key": contract.account_pj.account_key if contract.account_pj else None,
            "account_pf_key": contract.account_pf.account_key if contract.account_pf else None,
            "status": contract.status.enumerator if contract.status else None,
            "requested_amount": contract.requested_amount,
            "total_amount": contract.total_amount,
            "interest_rate_monthly": float(contract.interest_rate_monthly),
            "term_months": contract.term_months,
            "retention_percentage": float(contract.retention_percentage),
            "pocket_key": contract.pocket.pocket_key if contract.pocket else None,
            "installments": [
                {
                    "installment_key": inst.installment_key,
                    "installment_number": inst.installment_number,
                    "amount": inst.amount,
                    "principal_amount": inst.principal_amount,
                    "interest_amount": inst.interest_amount,
                    "due_date": inst.due_date.isoformat() if inst.due_date else None,
                    "paid_amount": inst.paid_amount,
                    "status": inst.status,
                }
                for inst in contract.installments
            ],
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
        }


class ReceivablesAnticipationDTO:
    @staticmethod
    def obj_to_dict(anticipation: ReceivablesAnticipation) -> dict:
        return {
            "anticipation_key": anticipation.anticipation_key,
            "account_key": anticipation.account.account_key if anticipation.account else None,
            "original_amount": anticipation.original_amount,
            "discount_fee": anticipation.discount_fee,
            "net_disbursed_amount": anticipation.net_disbursed_amount,
            "charge_ids": anticipation.charge_ids,
            "status": anticipation.status,
            "created_at": anticipation.created_at.isoformat() if anticipation.created_at else None,
        }
