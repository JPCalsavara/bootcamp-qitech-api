import random
import uuid

from tests.utils import ClientRequisition, RandomGenerator
from tests.utils import INTERNAL_TOKEN


class TestSchemaRejections:
    """COD-12: as 6 rotas non-GET recém-protegidas rejeitam corpo inválido com 400 (QIT000001)."""

    HEADERS = {"INTERNAL-TOKEN": INTERNAL_TOKEN}

    def _create_pj_account(self) -> str:
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"schema.{uuid.uuid4().hex[:8]}@exemplo.com.br"
        cnpj = RandomGenerator.generate_cnpj()

        payload = {
            "name": "Cliente Schema",
            "legal_name": "Cliente Schema MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1990-01-01",
            "phone": f"+5511{random_digits}0000",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }
        resp = ClientRequisition.send("POST", "/customer", payload=payload, headers=self.HEADERS)
        assert resp.response_status == 202
        customer_key = resp.response_json["customer_key"]

        resp_acc = ClientRequisition.send(
            "POST", f"/customer/{customer_key}/account", headers=self.HEADERS
        )
        accounts = resp_acc.response_json
        return next(a for a in accounts if a["type"] == "PJ")["account_key"]

    def _assert_bad_request(self, resp) -> None:
        assert resp.response_status == 400, f"esperado 400, veio {resp.response_status}: {resp.response_json}"
        assert resp.response_json["code"] == "QIT000001"

    def test_put_account_status_rejects_malformed_body(self) -> None:
        account_key = self._create_pj_account()
        resp = ClientRequisition.send(
            "PUT",
            f"/account/{account_key}/status",
            payload={"unexpected_field": "x"},  # falta 'status', campo desconhecido
            headers=self.HEADERS,
        )
        self._assert_bad_request(resp)

    def test_put_account_blocked_balance_rejects_malformed_body(self) -> None:
        account_key = self._create_pj_account()
        resp = ClientRequisition.send(
            "PUT",
            f"/account/{account_key}/blocked-balance",
            payload={"operation": "INVALID_OP", "amount": 0},  # enum inválido + amount < 1
            headers=self.HEADERS,
        )
        self._assert_bad_request(resp)

    def test_post_charge_reconciliation_rejects_malformed_body(self) -> None:
        resp = ClientRequisition.send(
            "POST",
            "/charge/reconciliation",
            payload={"charge_keys": "nao-e-uma-lista"},  # deveria ser array
            headers=self.HEADERS,
        )
        self._assert_bad_request(resp)

    def test_post_webhook_payment_rejects_malformed_body(self) -> None:
        resp = ClientRequisition.send(
            "POST",
            "/webhook/payment",
            payload={"event": "payment.settled"},  # falta 'charge_key' obrigatório
            headers=self.HEADERS,
        )
        self._assert_bad_request(resp)

    def test_post_settle_due_rejects_malformed_body(self) -> None:
        resp = ClientRequisition.send(
            "POST",
            "/credit/installment/settle-due",
            payload={"target_date": "2026-01-01", "campo_extra": True},  # additionalProperties
            headers=self.HEADERS,
        )
        self._assert_bad_request(resp)

    def test_post_pocket_deposit_rejects_malformed_body(self) -> None:
        account_key = self._create_pj_account()
        resp_pocket = ClientRequisition.send(
            "POST",
            f"/account/{account_key}/pocket",
            payload={"type": "PERSONALIZADO", "name": "Caixinha Schema"},
            headers=self.HEADERS,
        )
        pocket_key = resp_pocket.response_json["pocket_key"]

        resp = ClientRequisition.send(
            "POST",
            f"/account/{account_key}/pocket/{pocket_key}/deposit",
            payload={"amount": 0},  # minimo e 1
            headers=self.HEADERS,
        )
        self._assert_bad_request(resp)
