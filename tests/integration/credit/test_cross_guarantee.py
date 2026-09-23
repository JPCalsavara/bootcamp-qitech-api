from datetime import date, timedelta
import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestCrossGuarantee:
    """RFC 04: Garantia Cruzada Patrimonial PF/PJ por Inadimplência de CCB."""

    def _setup_customer_and_accounts(self):
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"cross.{random_digits}@exemplo.com.br"
        cnpj = f"12.345.678/{random_digits}-90"

        payload = {
            "name": "Cliente Garantia Cruzada",
            "legal_name": "Cliente Garantia Cruzada MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1990-05-15",
            "phone": "+5511977778888",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }

        resp = ClientRequisition.send("POST", "/customers", payload=payload, headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        customer_key = resp.response_json["customer_key"]

        resp_accounts = ClientRequisition.send(
            "POST",
            f"/customers/{customer_key}/accounts",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        accounts = resp_accounts.response_json
        pj_acc = next(a for a in accounts if a["type"] == "PJ")
        pf_acc = next(a for a in accounts if a["type"] == "PF")
        return customer_key, pj_acc["account_key"], pf_acc["account_key"]

    def _create_contract(self, customer_key: str, pj_key: str, pf_key: str) -> dict:
        contract_payload = {
            "customer_key": customer_key,
            "account_pj_key": pj_key,
            "account_pf_key": pf_key,
            "requested_amount": 600000,  # R$ 6.000,00
            "term_months": 6,
            "interest_rate_monthly": 0.02,
            "retention_percentage": 10.0,
        }
        resp = ClientRequisition.send(
            "POST",
            "/credit/contracts",
            payload=contract_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 201
        return resp.response_json

    def test_cross_guarantee_ignores_installments_within_grace_period(self) -> None:
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()
        contract = self._create_contract(customer_key, pj_key, pf_key)
        contract_key = contract["contract_key"]

        # Aporte de saldo na conta PF
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": pf_key, "amount": 500000},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        # Parcela 1 vence em today + 30 dias.
        # Simulamos data de corte com apenas 3 dias de atraso (dentro da carência de 5 dias).
        target_date = (date.today() + timedelta(days=33)).isoformat()

        resp = ClientRequisition.send(
            "POST",
            "/credit/cross-guarantee/execute",
            payload={"contract_key": contract_key, "target_date": target_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 200
        data = resp.response_json
        assert data["settled_installments"] == 0

        # Verifica que o saldo na conta PF não foi debitado
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pf_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 500000

        # Verifica contrato: parcela 1 continua OPEN
        resp_contract = ClientRequisition.send("GET", f"/credit/contracts/{contract_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_contract.response_json["installments"][0]["status"] == "OPEN"

    def test_cross_guarantee_settles_overdue_installment_from_personal_account(self) -> None:
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()
        contract = self._create_contract(customer_key, pj_key, pf_key)
        contract_key = contract["contract_key"]
        inst_1 = contract["installments"][0]
        inst_amount = inst_1["amount"]

        # Aporte de saldo na conta PF para cobrir a parcela
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": pf_key, "amount": 300000},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        # Parcela 1 vence em today + 30 dias.
        # Data de corte em today + 38 dias (8 dias após o vencimento > tolerância de 5 dias).
        target_date = (date.today() + timedelta(days=38)).isoformat()

        resp = ClientRequisition.send(
            "POST",
            "/credit/cross-guarantee/execute",
            payload={"contract_key": contract_key, "target_date": target_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 200
        data = resp.response_json
        assert data["settled_installments"] == 1
        assert data["total_settled_amount"] == inst_amount

        # Verifica saldo na conta PF: debitado exatamente no valor da parcela
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pf_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 300000 - inst_amount

        # Verifica contrato: parcela 1 agora está PAID
        resp_contract = ClientRequisition.send("GET", f"/credit/contracts/{contract_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_contract.response_json["installments"][0]["status"] == "PAID"
        assert resp_contract.response_json["installments"][0]["paid_amount"] == inst_amount

        # Verifica extrato PF: lançamento de débito da garantia cruzada registrado
        resp_stmt = ClientRequisition.send("GET", f"/accounts/{pf_key}/statement", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        entries = resp_stmt.response_json
        assert any(e["entry_type"] == "DEBIT" and e["amount"] == inst_amount and "Garantia Cruzada" in e["description"] for e in entries)

    def test_cross_guarantee_keeps_contract_overdue_when_personal_account_has_no_funds(self) -> None:
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()
        contract = self._create_contract(customer_key, pj_key, pf_key)
        contract_key = contract["contract_key"]

        # Conta PF não possui saldo (saldo = 0)
        target_date = (date.today() + timedelta(days=40)).isoformat()

        resp = ClientRequisition.send(
            "POST",
            "/credit/cross-guarantee/execute",
            payload={"contract_key": contract_key, "target_date": target_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 200
        data = resp.response_json
        assert data["settled_installments"] == 0

        # Verifica contrato: parcela 1 marcada como OVERDUE e contrato marcado como defaulted
        resp_contract = ClientRequisition.send("GET", f"/credit/contracts/{contract_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_contract.response_json["installments"][0]["status"] == "OVERDUE"
        assert resp_contract.response_json["status"] == "defaulted"
