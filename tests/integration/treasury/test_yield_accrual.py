import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestYieldAccrual:
    """RFC 06: Fluxo de Caixa Remunerado (CDB 100% CDI, Cash Sweep)."""

    def _setup_account_with_balance(self, amount: int = 100000) -> str:
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"yield.{random_digits}@exemplo.com.br"
        cnpj = f"12.345.678/{random_digits}-90"

        payload = {
            "name": "Cliente Rendimento",
            "legal_name": "Cliente Rendimento MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1994-09-05",
            "phone": "+5511944445555",
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
        pj_key = pj_acc["account_key"]

        # Aporte de saldo
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": pj_key, "amount": amount},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return pj_key

    def test_daily_cdi_yield_accrual_and_ledger_credit(self) -> None:
        pj_key = self._setup_account_with_balance(amount=1000000)  # R$ 10.000,00

        # Roda job de rendimento diário (taxa diária CDI ~0.00045)
        resp_accrue = ClientRequisition.send(
            "POST",
            "/treasury/accrue-yield",
            payload={"account_key": pj_key, "cdi_daily_rate": 0.00045},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_accrue.response_status == 200
        data = resp_accrue.response_json
        event = data["accrual_event"]
        assert event["gross_yield"] > 0
        assert event["ir_withheld"] > 0
        assert event["net_yield"] == event["gross_yield"] - event["ir_withheld"] - event["iof_withheld"]

        # Verifica crédito no Ledger com tipo TREASURY_YIELD
        resp_stmt = ClientRequisition.send("GET", f"/accounts/{pj_key}/statement", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        entries = resp_stmt.response_json
        assert any(e["entry_type"] == "CREDIT" and e["amount"] == event["net_yield"] for e in entries)

        # Consulta posição acumulada
        resp_pos = ClientRequisition.send("GET", f"/accounts/{pj_key}/yield-position", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_pos.response_status == 200
        pos = resp_pos.response_json
        assert pos["accumulated_yield"] == event["gross_yield"]
        assert pos["net_yield"] == event["net_yield"]
