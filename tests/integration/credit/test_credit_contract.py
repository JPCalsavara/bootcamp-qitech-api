import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestCreditContract:
    """RFC 05: Linhas de Crédito & Trava de Recebíveis."""

    def _setup_customer_and_accounts(self):
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"credit.{random_digits}@exemplo.com.br"
        cnpj = f"12.345.678/{random_digits}-90"

        payload = {
            "name": "Cliente Credito",
            "legal_name": "Cliente Credito MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1989-11-25",
            "phone": "+5511955554444",
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

    def test_credit_contract_creation_disbursement_and_installments(self) -> None:
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()

        contract_payload = {
            "customer_key": customer_key,
            "account_pj_key": pj_key,
            "account_pf_key": pf_key,
            "requested_amount": 500000,  # R$ 5.000,00
            "term_months": 6,
            "interest_rate_monthly": 0.02,
            "retention_percentage": 15.0,  # 15% de trava
        }

        resp_contract = ClientRequisition.send(
            "POST",
            "/credit/contracts",
            payload=contract_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_contract.response_status == 201
        contract = resp_contract.response_json
        assert contract["status"] == "disbursed"
        assert contract["requested_amount"] == 500000
        assert len(contract["installments"]) == 6
        assert contract["pocket_key"] is not None

        contract_key = contract["contract_key"]

        # Verifica saldo na conta PJ: R$ 5.000,00 desembolsados
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 500000

        # Consulta contrato via GET /credit/contracts/{contract_key}
        resp_get = ClientRequisition.send(
            "GET",
            f"/credit/contracts/{contract_key}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_get.response_status == 200
        assert resp_get.response_json["contract_key"] == contract_key
        assert len(resp_get.response_json["installments"]) == 6

    def test_receivables_anticipation(self) -> None:
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()

        anticipation_payload = {
            "account_key": pj_key,
            "charge_keys": ["charge-key-1", "charge-key-2"],
            "discount_rate": 0.05,  # 5% de taxa de desconto
        }

        resp = ClientRequisition.send(
            "POST",
            "/credit/anticipations",
            payload=anticipation_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 201
        data = resp.response_json
        assert data["status"] == "COMPLETED"
        assert data["discount_fee"] > 0
        assert data["net_disbursed_amount"] == data["original_amount"] - data["discount_fee"]

        # Verifica se o valor líquido foi creditado na conta
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == data["net_disbursed_amount"]
