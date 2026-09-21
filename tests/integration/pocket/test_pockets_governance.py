import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestPocketsGovernance:
    """RFC 07: Governança Patrimonial & Pockets (Caixinhas / Subcontas)."""

    def _setup_customer_and_accounts(self):
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"pocket.{random_digits}@exemplo.com.br"
        cnpj = f"12.345.678/{random_digits}-90"

        payload = {
            "name": "Cliente Governanca",
            "legal_name": "Cliente Governanca MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1995-12-01",
            "phone": "+5511933336666",
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

    def test_creates_and_lists_pockets(self) -> None:
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()

        # 1. Cria caixinha de reserva prioritária do DAS
        resp_pocket = ClientRequisition.send(
            "POST",
            f"/accounts/{pj_key}/pockets",
            payload={
                "type": "DAS_IMPOSTOS",
                "name": "Imposto DAS Mensal",
                "target_amount": 7500,  # R$ 75,00
                "is_locked": False,
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_pocket.response_status == 201
        pocket_data = resp_pocket.response_json
        assert pocket_data["type"] == "DAS_IMPOSTOS"
        assert pocket_data["target_amount"] == 7500
        assert pocket_data["current_balance"] == 0

        # 2. Lista caixinhas da conta PJ
        resp_list = ClientRequisition.send("GET", f"/accounts/{pj_key}/pockets", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_list.response_status == 200
        pockets = resp_list.response_json
        assert len(pockets) >= 1
        assert any(p["pocket_key"] == pocket_data["pocket_key"] for p in pockets)

    def test_transfer_policy_blocks_unreserved_das_transfer(self) -> None:
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()

        # Aporte de saldo na PJ
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": pj_key, "amount": 100000},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        # Cria caixinha do DAS com alvo R$ 75,00 (7500 centavos) vazia
        resp_pocket = ClientRequisition.send(
            "POST",
            f"/accounts/{pj_key}/pockets",
            payload={
                "type": "DAS_IMPOSTOS",
                "name": "DAS Reserva",
                "target_amount": 7500,
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        pocket_key = resp_pocket.response_json["pocket_key"]

        # Configura política exigindo checagem do DAS
        ClientRequisition.send(
            "POST",
            "/governance/transfer-policies",
            payload={
                "account_pj_key": pj_key,
                "account_pf_key": pf_key,
                "max_daily_transfer_amount": 50000,
                "das_reserved_check": True,
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        # Tentativa de transferir PJ -> PF antes de preencher o DAS é bloqueada (422)
        resp_transfer_fail = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload={
                "source_account_key": pj_key,
                "destination_account_key": pf_key,
                "amount": 10000,
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_transfer_fail.response_status == 422
        assert resp_transfer_fail.response_json["code"] == "QIT002009"

        # Deposita o valor na caixinha do DAS
        resp_dep = ClientRequisition.send(
            "POST",
            f"/accounts/{pj_key}/pockets/{pocket_key}/deposit",
            payload={"amount": 7500},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_dep.response_status == 200

        # Agora a transferência PJ -> PF deve ser autorizada
        resp_transfer_ok = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload={
                "source_account_key": pj_key,
                "destination_account_key": pf_key,
                "amount": 10000,
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_transfer_ok.response_status == 200
        assert resp_transfer_ok.response_json["status"] == "completed"

    def test_revenue_tracker_annual_limit(self) -> None:
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()

        resp_tracker = ClientRequisition.send(
            "GET",
            f"/customers/{customer_key}/revenue-tracker",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_tracker.response_status == 200
        data = resp_tracker.response_json
        assert data["annual_limit"] == 8100000
        assert data["accumulated_revenue"] == 0
        assert data["threshold_warning_sent"] is False
        assert data["threshold_danger_sent"] is False
