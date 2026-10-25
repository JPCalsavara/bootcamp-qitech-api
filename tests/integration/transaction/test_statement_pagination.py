import random

from tests.utils import ClientRequisition, RandomGenerator
from tests.utils import INTERNAL_TOKEN


class TestStatementPagination:
    """ESC-01: GET /account/{account_key}/statement honra limit/offset da query string."""

    def _setup_account(self):
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"statement.{random_digits}@exemplo.com.br"
        cnpj = RandomGenerator.generate_cnpj()

        payload = {
            "name": "Cliente Extrato",
            "legal_name": "Cliente Extrato MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1991-01-10",
            "phone": "+5511977773333",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }

        resp = ClientRequisition.send(
            "POST", "/customer", payload=payload, headers={"INTERNAL-TOKEN": INTERNAL_TOKEN}
        )
        assert resp.response_status == 202
        customer_key = resp.response_json["customer_key"]

        resp_accounts = ClientRequisition.send(
            "POST",
            f"/customer/{customer_key}/account",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        accounts = resp_accounts.response_json
        pj_acc = next(a for a in accounts if a["type"] == "PJ")
        return pj_acc["account_key"]

    def test_statement_pages_are_disjoint(self) -> None:
        account_key = self._setup_account()

        # Gera várias entradas no ledger via cash-ins repetidos.
        for i in range(5):
            resp_cash_in = ClientRequisition.send(
                "POST",
                "/cash-in",
                payload={"account_key": account_key, "amount": 1000 + i, "description": f"Aporte {i}"},
                headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
            )
            assert resp_cash_in.response_status == 200

        resp_page_1 = ClientRequisition.send(
            "GET",
            f"/account/{account_key}/statement",
            query_params={"limit": 2, "offset": 0},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        resp_page_2 = ClientRequisition.send(
            "GET",
            f"/account/{account_key}/statement",
            query_params={"limit": 2, "offset": 2},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        assert resp_page_1.response_status == 200
        assert resp_page_2.response_status == 200

        page_1_entries = resp_page_1.response_json
        page_2_entries = resp_page_2.response_json
        assert len(page_1_entries) == 2
        assert len(page_2_entries) == 2

        keys_page_1 = {e["entry_key"] for e in page_1_entries}
        keys_page_2 = {e["entry_key"] for e in page_2_entries}
        assert keys_page_1.isdisjoint(keys_page_2)

    def test_statement_negative_limit_returns_400(self) -> None:
        account_key = self._setup_account()

        resp = ClientRequisition.send(
            "GET",
            f"/account/{account_key}/statement",
            query_params={"limit": -1},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 400
        assert resp.response_json["code"] == "QIT000010"

    def test_statement_non_numeric_offset_returns_400(self) -> None:
        account_key = self._setup_account()

        resp = ClientRequisition.send(
            "GET",
            f"/account/{account_key}/statement",
            query_params={"offset": "abc"},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 400
        assert resp.response_json["code"] == "QIT000010"
