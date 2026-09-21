from datetime import date, timedelta
import hashlib
import hmac
import json
import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestChargesWebhook:
    """RFC 04: Meios de Pagamento, Liquidação e Webhooks HMAC (ADR-0008)."""

    WEBHOOK_SECRET = "qitech_bootcamp_secret_2026"

    def _setup_pj_account(self) -> str:
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"charge.{random_digits}@exemplo.com.br"
        cnpj = f"12.345.678/{random_digits}-90"

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

        resp = ClientRequisition.send("POST", "/customers", payload=payload, headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        customer_key = resp.response_json["customer_key"]

        resp_accounts = ClientRequisition.send(
            "POST",
            f"/customers/{customer_key}/accounts",
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
            f"/accounts/{pj_key}/charges",
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
            f"/accounts/{pj_key}/charges",
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
            f"/accounts/{pj_key}/charges",
            payload={"method": "CREDIT_CARD_LINK", "amount": 50000, "due_date": due_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_link.response_status == 201
        link_data = resp_link.response_json
        assert link_data["method"] == "CREDIT_CARD_LINK"
        assert link_data["fee_amount"] == int(50000 * 0.0299)
        assert "payment_url" in link_data and link_data["payment_url"] is not None

        # 4. Consulta cobrança via GET /charges/{charge_key}
        resp_get = ClientRequisition.send(
            "GET",
            f"/charges/{pix_data['charge_key']}",
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
            f"/accounts/{pj_key}/charges",
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
            "/webhooks/payments",
            payload=webhook_payload,
            headers={
                "INTERNAL-TOKEN": INTERNAL_TOKEN,
                "X-Signature-SHA256": sig,
            },
        )
        assert resp_wh.response_status == 200
        assert resp_wh.response_json["status"] == "processed"

        # Verifica cobrança marcada como 'paid'
        resp_get = ClientRequisition.send("GET", f"/charges/{charge_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_get.response_json["status"] == "paid"

        # Verifica saldo da conta PJ: bruto 20000 - taxa 90 = 19910 centavos
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 19910

        # Verifica extrato: crédito bruto + débito de tarifa (ADR-0008)
        resp_stmt = ClientRequisition.send("GET", f"/accounts/{pj_key}/statement", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        entries = resp_stmt.response_json
        assert any(e["entry_type"] == "CREDIT" and e["amount"] == 20000 for e in entries)
        assert any(e["entry_type"] == "DEBIT" and e["amount"] == 90 for e in entries)

    def test_webhook_invalid_signature_returns_401(self) -> None:
        pj_key = self._setup_pj_account()
        due_date = (date.today() + timedelta(days=3)).isoformat()

        resp_charge = ClientRequisition.send(
            "POST",
            f"/accounts/{pj_key}/charges",
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
            "/webhooks/payments",
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
            f"/accounts/{pj_key}/charges",
            payload={"method": "BOLETO", "amount": 30000, "due_date": due_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_charge.response_status == 201
        charge_data = resp_charge.response_json
        charge_key = charge_data["charge_key"]
        assert charge_data["status"] == "created"

        # Dispara job de reconciliação de cobranças
        resp_rec = ClientRequisition.send(
            "POST",
            "/charges/reconciliation",
            payload={"charge_keys": [charge_key]},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_rec.response_status == 200
        rec_data = resp_rec.response_json
        assert rec_data["reconciled_count"] >= 1
        assert rec_data["settled_amount"] >= 30000

        # Verifica cobrança marcada como 'paid'
        resp_get = ClientRequisition.send("GET", f"/charges/{charge_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_get.response_json["status"] == "paid"

        # Verifica saldo da conta PJ: bruto 30000 - taxa boleto 250 = 29750
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 29750

        # Idempotência: rodar a reconciliação novamente não duplica liquidação
        resp_rec2 = ClientRequisition.send(
            "POST",
            "/charges/reconciliation",
            payload={"charge_keys": [charge_key]},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_rec2.response_status == 200
        assert resp_rec2.response_json["reconciled_count"] == 0

        # Saldo permanece inalterado
        resp_bal2 = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal2.response_json["balance"] == 29750

