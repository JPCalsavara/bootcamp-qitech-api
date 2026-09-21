import random
import uuid
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestTransfers:
    """RFC 02: Ledger, Dijkstra Locks, Partidas Dobradas e Idempotência."""

    def _setup_customer_and_accounts(self):
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"ledger.{random_digits}@exemplo.com.br"
        cnpj = f"12.345.678/{random_digits}-90"

        payload = {
            "name": "Cliente Ledger",
            "legal_name": "Cliente Ledger MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1991-01-10",
            "phone": "+5511977772222",
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
        return pj_acc["account_key"], pf_acc["account_key"]

    def test_internal_transfer_success_and_ledger_double_entry(self) -> None:
        pj_key, pf_key = self._setup_customer_and_accounts()

        # 1. Cash-in na conta PJ: R$ 500,00 (50000 centavos)
        resp_cash_in = ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": pj_key, "amount": 50000, "description": "Aporte inicial"},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_cash_in.response_status == 200

        # 2. Transferência de R$ 200,00 (20000 centavos) PJ -> PF
        transfer_payload = {
            "source_account_key": pj_key,
            "destination_account_key": pf_key,
            "amount": 20000,
            "description": "Pró-labore parcial",
        }
        resp_transfer = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload=transfer_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_transfer.response_status == 200
        tx = resp_transfer.response_json
        assert tx["status"] == "completed"
        assert tx["amount"] == 20000

        # 3. Verifica saldos atualizados
        resp_pj_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_pj_bal.response_json["balance"] == 30000

        resp_pf_bal = ClientRequisition.send("GET", f"/accounts/{pf_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_pf_bal.response_json["balance"] == 20000

        # 4. Verifica extrato (Ledger) com partidas dobradas
        resp_stmt_pj = ClientRequisition.send("GET", f"/accounts/{pj_key}/statement", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        entries_pj = resp_stmt_pj.response_json
        assert any(e["entry_type"] == "DEBIT" and e["amount"] == 20000 and e["balance_after"] == 30000 for e in entries_pj)

        resp_stmt_pf = ClientRequisition.send("GET", f"/accounts/{pf_key}/statement", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        entries_pf = resp_stmt_pf.response_json
        assert any(e["entry_type"] == "CREDIT" and e["amount"] == 20000 and e["balance_after"] == 20000 for e in entries_pf)

    def test_transfer_insufficient_funds_returns_422(self) -> None:
        pj_key, pf_key = self._setup_customer_and_accounts()

        # Tentativa de transferir sem saldo
        transfer_payload = {
            "source_account_key": pj_key,
            "destination_account_key": pf_key,
            "amount": 100000,
            "description": "Transferência sem saldo",
        }
        resp = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload=transfer_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 422
        assert resp.response_json["code"] == "QIT002005"

    def test_transfer_idempotency_prevents_duplicate_execution(self) -> None:
        pj_key, pf_key = self._setup_customer_and_accounts()

        # Aporte inicial: R$ 300,00
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": pj_key, "amount": 30000},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        idempotency_key = str(uuid.uuid4())
        transfer_payload = {
            "source_account_key": pj_key,
            "destination_account_key": pf_key,
            "amount": 10000,
            "description": "Transferência com Idempotência",
        }

        # 1ª chamada com a chave
        resp1 = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload=transfer_payload,
            headers={
                "INTERNAL-TOKEN": INTERNAL_TOKEN,
                "Idempotency-Key": idempotency_key,
            },
        )
        assert resp1.response_status == 200

        # 2ª chamada idêntica com a mesma chave
        resp2 = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload=transfer_payload,
            headers={
                "INTERNAL-TOKEN": INTERNAL_TOKEN,
                "Idempotency-Key": idempotency_key,
            },
        )
        assert resp2.response_status == 200
        assert resp1.response_json == resp2.response_json

        # Saldo deve ter sido debitado apenas UMA vez (30000 - 10000 = 20000)
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 20000
