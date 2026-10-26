from datetime import date, timedelta
from os import environ
import hashlib
import hmac
import json
import random

import requests

from tests.utils import ClientRequisition, RandomGenerator
from tests.utils import INTERNAL_TOKEN


def _mockserver_base_url() -> str:
    host = environ.get("SERVER_LOCALHOST", "0.0.0.0")
    port = environ.get("MOCKSERVER_PORT", "1080")
    return f"http://{host}:{port}"


class TestChargesWebhook:
    """RFC 04: Meios de Pagamento, Liquidação e Webhooks HMAC (ADR-0008)."""

    WEBHOOK_SECRET = "qitech_bootcamp_secret_2026"

    def _prime_charge_status_paid(self) -> None:
        """Com MOCK_EXTERNAL_SERVICES=false (docker-compose.yml), o PaymentConnector
        faz HTTP de verdade contra o MockServer. Para que a reconciliação ativa
        (GET /payments/charges/{key}/status) enxergue a cobrança como liquidada,
        este teste prima a expectation correspondente — do mesmo jeito que os
        testes em tests/integration/connectors/. Sem priming, o mock responde o
        padrão e nada é reconciliado."""
        base_url = _mockserver_base_url()
        expectation = {
            "httpRequest": {"method": "GET", "path": "/payments/charges/[^/]+/status"},
            "httpResponse": {
                "statusCode": 200,
                "headers": {"content-type": ["application/json"]},
                "body": {"status": "PAID"},
            },
        }
        resp = requests.put(f"{base_url}/mockserver/expectation", json=expectation, timeout=5)
        assert resp.status_code in (200, 201), f"falha ao primar expectation: {resp.status_code} {resp.text}"

    def _setup_pj_account(self) -> str:
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"charge.{random_digits}@exemplo.com.br"
        cnpj = RandomGenerator.generate_cnpj()

        payload = {
            "name": "Cliente Cobranca",
            "legal_name": "Cliente Cobranca MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1993-04-18",
            "phone": "+5511966663333",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }

        resp = ClientRequisition.send("POST", "/customer", payload=payload, headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        customer_key = resp.response_json["customer_key"]

        resp_accounts = ClientRequisition.send(
            "POST",
            f"/customer/{customer_key}/account",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        accounts = resp_accounts.response_json
        pj_acc = next(a for a in accounts if a["type"] == "PJ")
        return pj_acc["account_key"]

    def test_creates_charges_for_pix_boleto_and_card_link(self) -> None:
        pj_key = self._setup_pj_account()
        due_date = (date.today() + timedelta(days=7)).isoformat()

        # 1. PIX
        resp_pix = ClientRequisition.send(
            "POST",
            f"/account/{pj_key}/charge",
            payload={"method": "PIX", "amount": 10000, "due_date": due_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_pix.response_status == 201
        pix_data = resp_pix.response_json
        assert pix_data["method"] == "PIX"
        assert pix_data["fee_amount"] == 90  # R$ 0,90
        assert pix_data["net_amount"] == 9910
        assert "qr_code" in pix_data and pix_data["qr_code"] is not None

        # 2. BOLETO
        resp_boleto = ClientRequisition.send(
            "POST",
            f"/account/{pj_key}/charge",
            payload={"method": "BOLETO", "amount": 25000, "due_date": due_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_boleto.response_status == 201
        bol_data = resp_boleto.response_json
        assert bol_data["method"] == "BOLETO"
        assert bol_data["fee_amount"] == 250  # R$ 2,50
        assert bol_data["net_amount"] == 24750
        assert "barcode" in bol_data and bol_data["barcode"] is not None

        # 3. CREDIT_CARD_LINK
        resp_link = ClientRequisition.send(
            "POST",
            f"/account/{pj_key}/charge",
            payload={"method": "CREDIT_CARD_LINK", "amount": 50000, "due_date": due_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_link.response_status == 201
        link_data = resp_link.response_json
        assert link_data["method"] == "CREDIT_CARD_LINK"
        assert link_data["fee_amount"] == int(50000 * 0.0299)
        assert "payment_url" in link_data and link_data["payment_url"] is not None

        # 4. Consulta cobrança via GET /charge/{charge_key}
        resp_get = ClientRequisition.send(
            "GET",
            f"/charge/{pix_data['charge_key']}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_get.response_status == 200
        assert resp_get.response_json["charge_key"] == pix_data["charge_key"]

    def test_webhook_payment_settlement_and_atomic_fee_debit(self) -> None:
        pj_key = self._setup_pj_account()
        due_date = (date.today() + timedelta(days=3)).isoformat()

        # Cria cobrança PIX de R$ 200,00 (20000 centavos)
        resp_charge = ClientRequisition.send(
            "POST",
            f"/account/{pj_key}/charge",
            payload={"method": "PIX", "amount": 20000, "due_date": due_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        charge = resp_charge.response_json
        charge_key = charge["charge_key"]

        # Dispara Webhook com HMAC válido
        webhook_payload = {
            "event": "payment.settled",
            "charge_key": charge_key,
            "amount": 20000,
        }
        payload_bytes = json.dumps(webhook_payload, sort_keys=True).encode("utf-8")
        sig = hmac.new(self.WEBHOOK_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

        resp_wh = ClientRequisition.send(
            "POST",
            "/webhook/payment",
            payload=webhook_payload,
            headers={
                "INTERNAL-TOKEN": INTERNAL_TOKEN,
                "X-Signature-SHA256": sig,
            },
        )
        assert resp_wh.response_status == 200
        assert resp_wh.response_json["status"] == "processed"

        # Verifica cobrança marcada como 'paid'
        resp_get = ClientRequisition.send("GET", f"/charge/{charge_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_get.response_json["status"] == "paid"

        # Verifica saldo da conta PJ: bruto 20000 - taxa 90 = 19910 centavos
        resp_bal = ClientRequisition.send("GET", f"/account/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 19910

        # Verifica extrato: crédito bruto + débito de tarifa (ADR-0008)
        resp_stmt = ClientRequisition.send("GET", f"/account/{pj_key}/statement", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        entries = resp_stmt.response_json
        assert any(e["entry_type"] == "CREDIT" and e["amount"] == 20000 for e in entries)
        assert any(e["entry_type"] == "DEBIT" and e["amount"] == 90 for e in entries)

    def test_webhook_invalid_signature_returns_401(self) -> None:
        pj_key = self._setup_pj_account()
        due_date = (date.today() + timedelta(days=3)).isoformat()

        resp_charge = ClientRequisition.send(
            "POST",
            f"/account/{pj_key}/charge",
            payload={"method": "PIX", "amount": 10000, "due_date": due_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        charge_key = resp_charge.response_json["charge_key"]

        webhook_payload = {
            "event": "payment.settled",
            "charge_key": charge_key,
            "amount": 10000,
        }

        resp = ClientRequisition.send(
            "POST",
            "/webhook/payment",
            payload=webhook_payload,
            headers={
                "INTERNAL-TOKEN": INTERNAL_TOKEN,
                "X-Signature-SHA256": "invalid_signature_hash",
            },
        )
        assert resp.response_status == 401
        assert resp.response_json["code"] == "QIT002008"

    def test_charges_reconciliation_job_settles_pending_charges(self) -> None:
        pj_key = self._setup_pj_account()
        due_date = (date.today() + timedelta(days=7)).isoformat()

        # Cria cobrança de Boleto (R$ 300,00) - que aguarda reconciliação ativa (polling de saída)
        resp_charge = ClientRequisition.send(
            "POST",
            f"/account/{pj_key}/charge",
            payload={"method": "BOLETO", "amount": 30000, "due_date": due_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_charge.response_status == 201
        charge_data = resp_charge.response_json
        charge_key = charge_data["charge_key"]
        assert charge_data["status"] == "created"

        # Prima o status PAID no gateway externo (MockServer) antes da conciliação.
        self._prime_charge_status_paid()

        # Dispara job de reconciliação de cobranças
        resp_rec = ClientRequisition.send(
            "POST",
            "/charge/reconciliation",
            payload={"charge_keys": [charge_key]},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_rec.response_status == 200
        rec_data = resp_rec.response_json
        assert rec_data["reconciled_count"] >= 1
        assert rec_data["settled_amount"] >= 30000

        # Verifica cobrança marcada como 'paid'
        resp_get = ClientRequisition.send("GET", f"/charge/{charge_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_get.response_json["status"] == "paid"

        # Verifica saldo da conta PJ: bruto 30000 - taxa boleto 250 = 29750
        resp_bal = ClientRequisition.send("GET", f"/account/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 29750

        # Idempotência: rodar a reconciliação novamente não duplica liquidação
        resp_rec2 = ClientRequisition.send(
            "POST",
            "/charge/reconciliation",
            payload={"charge_keys": [charge_key]},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_rec2.response_status == 200
        assert resp_rec2.response_json["reconciled_count"] == 0

        # Saldo permanece inalterado
        resp_bal2 = ClientRequisition.send("GET", f"/account/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal2.response_json["balance"] == 29750

    def test_charge_idempotency_prevents_duplicate_charge(self) -> None:
        pj_key = self._setup_pj_account()
        due_date = (date.today() + timedelta(days=5)).isoformat()
        idempotency_key = f"idem-charge-{random.randint(100000, 999999)}"

        payload = {"method": "PIX", "amount": 15000, "due_date": due_date}
        headers = {
            "INTERNAL-TOKEN": INTERNAL_TOKEN,
            "Idempotency-Key": idempotency_key,
        }

        # 1ª chamada
        resp1 = ClientRequisition.send(
            "POST",
            f"/account/{pj_key}/charge",
            payload=payload,
            headers=headers,
        )
        assert resp1.response_status == 201
        charge1 = resp1.response_json

        # 2ª chamada com mesma chave de idempotência
        resp2 = ClientRequisition.send(
            "POST",
            f"/account/{pj_key}/charge",
            payload=payload,
            headers=headers,
        )
        assert resp2.response_status == 201
        charge2 = resp2.response_json

        # Mesma chave de idempotência retorna a mesma cobrança em cache
        assert charge1["charge_key"] == charge2["charge_key"]
        assert charge1["amount"] == charge2["amount"]
