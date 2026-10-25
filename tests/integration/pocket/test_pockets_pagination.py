import random

from tests.utils import ClientRequisition, RandomGenerator
from tests.utils import INTERNAL_TOKEN


class TestPocketsPagination:
    """COD-10: GET /account/{account_key}/pockets honra limit/offset da query string."""

    def _setup_pj_account(self) -> str:
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"pocketpage.{random_digits}@exemplo.com.br"
        cnpj = RandomGenerator.generate_cnpj()

        payload = {
            "name": "Cliente Paginacao Pockets",
            "legal_name": "Cliente Paginacao Pockets MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1993-03-03",
            "phone": "+5511955554444",
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

    def test_pockets_pages_are_disjoint(self) -> None:
        account_key = self._setup_pj_account()

        # Cria mais de 2 caixinhas para ter páginas distintas.
        pocket_types = ["DAS_IMPOSTOS", "RESERVA_EMERGENCIA", "PRO_LABORE", "PERSONALIZADO"]
        for i, ptype in enumerate(pocket_types):
            resp = ClientRequisition.send(
                "POST",
                f"/account/{account_key}/pocket",
                payload={"type": ptype, "name": f"Caixinha {i}"},
                headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
            )
            assert resp.response_status == 201

        resp_page_1 = ClientRequisition.send(
            "GET",
            f"/account/{account_key}/pockets",
            query_params={"limit": 2, "offset": 0},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        resp_page_2 = ClientRequisition.send(
            "GET",
            f"/account/{account_key}/pockets",
            query_params={"limit": 2, "offset": 2},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        assert resp_page_1.response_status == 200
        assert resp_page_2.response_status == 200

        page_1 = resp_page_1.response_json
        page_2 = resp_page_2.response_json
        assert len(page_1) == 2
        assert len(page_2) == 2

        keys_page_1 = {p["pocket_key"] for p in page_1}
        keys_page_2 = {p["pocket_key"] for p in page_2}
        assert keys_page_1.isdisjoint(keys_page_2)

    def test_pockets_invalid_limit_returns_400(self) -> None:
        account_key = self._setup_pj_account()

        resp = ClientRequisition.send(
            "GET",
            f"/account/{account_key}/pockets",
            query_params={"limit": -5},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 400
        assert resp.response_json["code"] == "QIT000010"
