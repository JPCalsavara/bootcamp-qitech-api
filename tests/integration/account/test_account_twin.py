import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestAccountTwin:
    """RFC 01: Core Customer & Twin Accounts (PF/PJ)."""

    def test_creates_and_queries_twin_accounts(self) -> None:
        # 1. Cria customer
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"titular.{random_digits}@exemplo.com.br"
        cnpj = f"12.345.678/{random_digits}-90"

        payload = {
            "name": "Titular MEI",
            "legal_name": "Titular MEI Servicos Digitais LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1992-07-20",
            "phone": "+5511999990000",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }

        resp_customer = ClientRequisition.send(
            "POST",
            "/customers",
            payload=payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_customer.response_status == 202
        customer_key = resp_customer.response_json["customer_key"]

        # 2. Provisiona contas gêmeas (PF e PJ)
        resp_accounts = ClientRequisition.send(
            "POST",
            f"/customers/{customer_key}/accounts",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_accounts.response_status == 201
        accounts = resp_accounts.response_json
        assert len(accounts) == 2

        types = {acc["type"] for acc in accounts}
        assert types == {"PF", "PJ"}

        for acc in accounts:
            assert acc["status"] == "active"
            assert acc["balance"] == 0
            assert "account_key" in acc
            assert "account_number" in acc

        # 3. Lista contas do customer via GET /customers/{customer_key}/accounts
        resp_list = ClientRequisition.send(
            "GET",
            f"/customers/{customer_key}/accounts",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_list.response_status == 200
        assert len(resp_list.response_json) == 2

        # 4. Consulta conta individual via GET /accounts/{account_key}
        pj_key = next(acc["account_key"] for acc in accounts if acc["type"] == "PJ")
        resp_get = ClientRequisition.send(
            "GET",
            f"/accounts/{pj_key}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_get.response_status == 200
        assert resp_get.response_json["account_key"] == pj_key

        # 5. Consulta saldo via GET /accounts/{account_key}/balance
        resp_balance = ClientRequisition.send(
            "GET",
            f"/accounts/{pj_key}/balance",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_balance.response_status == 200
        assert resp_balance.response_json["balance"] == 0
