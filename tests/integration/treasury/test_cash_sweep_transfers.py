import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestCashSweepTransfers:
    """RFC 03: Cash Sweep Automático e Invisível em Transferências."""

    def _setup_customer_account(self, name: str) -> tuple[str, str]:
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"sweep.{random_digits}@exemplo.com.br"
        cnpj = f"12.345.678/{random_digits}-90"

        payload = {
            "name": name,
            "legal_name": f"{name} MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1992-04-12",
            "phone": "+5511988887777",
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
        return customer_key, pj_acc["account_key"]

    def test_transfer_with_sufficient_free_balance_does_not_trigger_sweep(self) -> None:
        _, src_key = self._setup_customer_account("Cliente Origem A")
        _, dst_key = self._setup_customer_account("Cliente Destino A")

        # Aporte de R$ 1.000,00 na conta de origem
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": src_key, "amount": 100000},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        # Investe R$ 500,00 em CDB
        resp_invest = ClientRequisition.send(
            "POST",
            "/treasury/invest",
            payload={"account_key": src_key, "amount": 50000},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_invest.response_status == 200

        # Saldo livre agora é R$ 500,00 (50000 centavos) e CDB tem 50000 centavos
        # Transfere R$ 200,00 (20000 centavos) -> Saldo livre é suficiente!
        resp_tx = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload={
                "source_account_key": src_key,
                "destination_account_key": dst_key,
                "amount": 20000,
                "description": "Pagamento Fornecedor",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_tx.response_status == 200

        # Verifica saldo livre: 50000 - 20000 = 30000
        resp_bal = ClientRequisition.send("GET", f"/accounts/{src_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 30000

        # Verifica saldo no destino: 20000
        resp_dst_bal = ClientRequisition.send("GET", f"/accounts/{dst_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_dst_bal.response_json["balance"] == 20000

        # Verifica posição de CDB: permanece inalterada em 50000
        resp_pos = ClientRequisition.send("GET", f"/accounts/{src_key}/yield-position", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_pos.response_json["principal_amount"] == 50000

    def test_transfer_with_insufficient_free_balance_triggers_automatic_cash_sweep_from_cdb(self) -> None:
        _, src_key = self._setup_customer_account("Cliente Origem B")
        _, dst_key = self._setup_customer_account("Cliente Destino B")

        # Aporte de R$ 1.000,00 na conta de origem
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": src_key, "amount": 100000},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        # Investe R$ 950,00 em CDB (deixando apenas R$ 50,00 = 5000 centavos de saldo livre)
        resp_invest = ClientRequisition.send(
            "POST",
            "/treasury/invest",
            payload={"account_key": src_key, "amount": 95000},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_invest.response_status == 200

        # Saldo livre: 5.000 centavos. Saldo em CDB: 95.000 centavos.
        # Transfere R$ 200,00 (20.000 centavos). Déficit: 15.000 centavos.
        resp_tx = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload={
                "source_account_key": src_key,
                "destination_account_key": dst_key,
                "amount": 20000,
                "description": "Transferência com Cash Sweep Automático",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_tx.response_status == 200

        # Saldo livre após a transferência: 5000 + 15000 (resgate) - 20000 (débito) = 0
        resp_bal = ClientRequisition.send("GET", f"/accounts/{src_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 0

        # Destino recebeu os 20000
        resp_dst_bal = ClientRequisition.send("GET", f"/accounts/{dst_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_dst_bal.response_json["balance"] == 20000

        # Posição de CDB: 95000 - 15000 = 80000
        resp_pos = ClientRequisition.send("GET", f"/accounts/{src_key}/yield-position", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_pos.response_json["principal_amount"] == 80000

        # Verifica extrato da conta de origem: deve conter o resgate do Cash Sweep
        resp_stmt = ClientRequisition.send("GET", f"/accounts/{src_key}/statement", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        entries = resp_stmt.response_json
        assert any(e["entry_type"] == "CREDIT" and e["amount"] == 15000 and "Cash Sweep" in e["description"] for e in entries)

    def test_transfer_exceeding_both_free_and_cdb_balance_fails_with_422(self) -> None:
        _, src_key = self._setup_customer_account("Cliente Origem C")
        _, dst_key = self._setup_customer_account("Cliente Destino C")

        # Aporte de R$ 100,00 na conta de origem
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": src_key, "amount": 10000},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        # Investe R$ 60,00 em CDB (saldo livre: R$ 40,00 = 4000 centavos, CDB: 6000 centavos)
        resp_invest = ClientRequisition.send(
            "POST",
            "/treasury/invest",
            payload={"account_key": src_key, "amount": 6000},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_invest.response_status == 200

        # Total disponível (livre + CDB) = 10000 centavos (R$ 100,00)
        # Tenta transferir R$ 150,00 (15000 centavos) -> Deve falhar com 422
        resp_tx = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload={
                "source_account_key": src_key,
                "destination_account_key": dst_key,
                "amount": 15000,
                "description": "Transferência Impossível",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_tx.response_status == 422
        assert resp_tx.response_json["code"] == "QIT002005"

        # Saldos permanecem inalterados
        resp_bal = ClientRequisition.send("GET", f"/accounts/{src_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 4000

        resp_pos = ClientRequisition.send("GET", f"/accounts/{src_key}/yield-position", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_pos.response_json["principal_amount"] == 6000
