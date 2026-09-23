from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import json
import random
import time
from uuid import uuid4

from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestWebhookReplayAndDualSecret:
    """Roadmap Segurança 1.2: Proteção contra Replay Attacks, Nonce, Timestamp e Rotação Dual-Secret."""

    CURRENT_SECRET = "qitech_bootcamp_secret_2026"
    PREVIOUS_SECRET = "qitech_bootcamp_old_secret_2025"

    def _setup_pj_account_and_charge(self, amount: int = 15000) -> tuple[str, str]:
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"sec.{random_digits}@exemplo.com.br"
        cnpj = f"12.345.678/{random_digits}-90"

        payload = {
            "name": "Cliente Webhook Seguranca",
            "legal_name": "Cliente Webhook Seguranca MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1991-08-10",
            "phone": "+5511977771111",
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

        due_date = (date.today() + timedelta(days=5)).isoformat()
        resp_charge = ClientRequisition.send(
            "POST",
            f"/accounts/{pj_key}/charges",
            payload={"method": "PIX", "amount": amount, "due_date": due_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_charge.response_status == 201
        charge_key = resp_charge.response_json["charge_key"]
        return pj_key, charge_key

    def test_webhook_accepts_valid_timestamp_and_nonce(self) -> None:
        pj_key, charge_key = self._setup_pj_account_and_charge()
        nonce = str(uuid4())
        timestamp = str(int(time.time()))

        webhook_payload = {
            "event": "payment.settled",
            "charge_key": charge_key,
            "amount": 15000,
        }
        payload_bytes = json.dumps(webhook_payload, sort_keys=True).encode("utf-8")
        sig = hmac.new(self.CURRENT_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

        resp = ClientRequisition.send(
            "POST",
            "/webhooks/payments",
            payload=webhook_payload,
            headers={
                "INTERNAL-TOKEN": INTERNAL_TOKEN,
                "X-Signature-SHA256": sig,
                "X-Webhook-Timestamp": timestamp,
                "X-Webhook-Nonce": nonce,
            },
        )
        assert resp.response_status == 200
        assert resp.response_json["status"] == "processed"

    def test_webhook_rejects_expired_timestamp(self) -> None:
        pj_key, charge_key = self._setup_pj_account_and_charge()
        nonce = str(uuid4())
        # Timestamp de 10 minutos atrás (> 5 minutos = 300 segundos de tolerância)
        expired_timestamp = str(int(time.time() - 600))

        webhook_payload = {
            "event": "payment.settled",
            "charge_key": charge_key,
            "amount": 15000,
        }
        payload_bytes = json.dumps(webhook_payload, sort_keys=True).encode("utf-8")
        sig = hmac.new(self.CURRENT_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

        resp = ClientRequisition.send(
            "POST",
            "/webhooks/payments",
            payload=webhook_payload,
            headers={
                "INTERNAL-TOKEN": INTERNAL_TOKEN,
                "X-Signature-SHA256": sig,
                "X-Webhook-Timestamp": expired_timestamp,
                "X-Webhook-Nonce": nonce,
            },
        )
        assert resp.response_status == 401
        assert resp.response_json["code"] == "QIT002011"

    def test_webhook_rejects_replay_attack_duplicate_nonce(self) -> None:
        pj_key, charge_key = self._setup_pj_account_and_charge()
        fixed_nonce = f"nonce-{uuid4()}"
        timestamp = str(int(time.time()))

        webhook_payload = {
            "event": "payment.settled",
            "charge_key": charge_key,
            "amount": 15000,
        }
        payload_bytes = json.dumps(webhook_payload, sort_keys=True).encode("utf-8")
        sig = hmac.new(self.CURRENT_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

        # 1. Primeira requisição com o nonce deve ser aceita
        resp1 = ClientRequisition.send(
            "POST",
            "/webhooks/payments",
            payload=webhook_payload,
            headers={
                "INTERNAL-TOKEN": INTERNAL_TOKEN,
                "X-Signature-SHA256": sig,
                "X-Webhook-Timestamp": timestamp,
                "X-Webhook-Nonce": fixed_nonce,
            },
        )
        assert resp1.response_status == 200

        # 2. Segunda requisição com o MESMO nonce (ataque de repetição) deve ser rejeitada
        resp2 = ClientRequisition.send(
            "POST",
            "/webhooks/payments",
            payload=webhook_payload,
            headers={
                "INTERNAL-TOKEN": INTERNAL_TOKEN,
                "X-Signature-SHA256": sig,
                "X-Webhook-Timestamp": timestamp,
                "X-Webhook-Nonce": fixed_nonce,
            },
        )
        assert resp2.response_status == 409
        assert resp2.response_json["code"] == "QIT002012"

    def test_webhook_accepts_previous_secret_during_rotation(self) -> None:
        pj_key, charge_key = self._setup_pj_account_and_charge()
        nonce = str(uuid4())
        timestamp = str(int(time.time()))

        webhook_payload = {
            "event": "payment.settled",
            "charge_key": charge_key,
            "amount": 15000,
        }
        payload_bytes = json.dumps(webhook_payload, sort_keys=True).encode("utf-8")
        # Assina com a chave antiga (PREVIOUS_SECRET)
        sig_old = hmac.new(self.PREVIOUS_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

        resp = ClientRequisition.send(
            "POST",
            "/webhooks/payments",
            payload=webhook_payload,
            headers={
                "INTERNAL-TOKEN": INTERNAL_TOKEN,
                "X-Signature-SHA256": sig_old,
                "X-Webhook-Timestamp": timestamp,
                "X-Webhook-Nonce": nonce,
            },
        )
        assert resp.response_status == 200
        assert resp.response_json["status"] == "processed"
