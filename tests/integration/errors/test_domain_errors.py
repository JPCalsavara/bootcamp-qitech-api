"""COD-03: um teste de integração caixa-preta por erro de domínio que, até
aqui, nenhum teste provocava. Cada caso dispara a condição pela API (rotas
singulares renomeadas na FEAT-004) e confere o par (status HTTP, code).

São caixa-preta (ADR-0001): falam com a API viva por HTTP via ClientRequisition,
mandam o header INTERNAL-TOKEN, não importam de src e não tocam no banco.

Os erros de serviço externo (QIT002013 ExternalServiceTimeout e QIT002014
ExternalServiceUnavailable) ficam em test_external_service_errors.py, porque
dependem do MockServer (FEAT-005).
"""

import random
import uuid

from tests.utils import ClientRequisition, RandomGenerator
from tests.utils import INTERNAL_TOKEN


HEADERS = {"INTERNAL-TOKEN": INTERNAL_TOKEN}


def _customer_payload() -> dict:
    random_suffix = str(uuid.uuid4())[:8]
    return {
        "name": "Cliente Erros",
        "legal_name": "Cliente Erros MEI LTDA",
        "email": f"erros.{random_suffix}@exemplo.com.br",
        "cpf": RandomGenerator.generate_cpf(),
        "cnpj": RandomGenerator.generate_cnpj(),
        "birthdate": "1990-01-01",
        "phone": "+5511977770000",
        "password": "SenhaForte@2026",
        "transaction_pin": "1234",
    }


def _create_customer() -> str:
    resp = ClientRequisition.send("POST", "/customer", payload=_customer_payload(), headers=HEADERS)
    assert resp.response_status == 202, resp.response_json
    return resp.response_json["customer_key"]


def _create_pj_account() -> str:
    customer_key = _create_customer()
    resp = ClientRequisition.send("POST", f"/customer/{customer_key}/account", headers=HEADERS)
    assert resp.response_status == 201, resp.response_json
    return next(a for a in resp.response_json if a["type"] == "PJ")["account_key"]


class TestCustomerDomainErrors:
    def test_duplicated_cnpj_returns_409_qit001009(self) -> None:
        """POST /customer duas vezes com o mesmo CNPJ -> 409 DuplicatedCNPJ."""
        payload = _customer_payload()

        first = ClientRequisition.send("POST", "/customer", payload=payload, headers=HEADERS)
        assert first.response_status == 202

        # Reaproveita o CNPJ, trocando os demais documentos únicos para
        # que a colisão seja exatamente a do CNPJ (e não CPF/e-mail).
        duplicate = _customer_payload()
        duplicate["cnpj"] = payload["cnpj"]

        resp = ClientRequisition.send("POST", "/customer", payload=duplicate, headers=HEADERS)
        assert resp.response_status == 409
        assert resp.response_json["code"] == "QIT001009"

    def test_invalid_cnpj_returns_422_qit001008(self) -> None:
        """POST /customer com CNPJ de dígito verificador inválido -> 422 InvalidCNPJ."""
        payload = _customer_payload()
        # Formato perfeito, dígitos verificadores impossíveis ("00").
        payload["cnpj"] = "12.345.678/0001-00"

        resp = ClientRequisition.send("POST", "/customer", payload=payload, headers=HEADERS)
        assert resp.response_status == 422
        assert resp.response_json["code"] == "QIT001008"

    def test_not_found_customer_returns_404_qit002001(self) -> None:
        """GET /customer/{uuid aleatório} -> 404 NotFoundCustomer."""
        resp = ClientRequisition.send("GET", f"/customer/{uuid.uuid4()}", headers=HEADERS)
        assert resp.response_status == 404
        assert resp.response_json["code"] == "QIT002001"

    def test_customer_not_active_blocks_account_creation_qit002006(self) -> None:
        """Cliente reprovado no KYC (score baixo -> 'rejected') não abre conta.

        POST /account para um cliente em estado terminal -> 422 CustomerNotActive.
        """
        customer_key = _create_customer()

        # Score < 300 leva o cliente a 'rejected' (KycController.analyze).
        reject = ClientRequisition.send(
            "POST",
            f"/customer/{customer_key}/kyc/analysis",
            payload={"score": 150, "risk_tier": "HIGH"},
            headers=HEADERS,
        )
        assert reject.response_status == 200
        assert reject.response_json["customer_status"] == "rejected"

        resp = ClientRequisition.send("POST", f"/customer/{customer_key}/account", headers=HEADERS)
        assert resp.response_status == 422
        assert resp.response_json["code"] == "QIT002006"


class TestAccountDomainErrors:
    def test_not_found_account_returns_404_qit002002(self) -> None:
        """GET /account/{uuid aleatório} -> 404 NotFoundAccount."""
        resp = ClientRequisition.send("GET", f"/account/{uuid.uuid4()}", headers=HEADERS)
        assert resp.response_status == 404
        assert resp.response_json["code"] == "QIT002002"

    def test_account_status_not_found_returns_400_qit002010(self) -> None:
        """PUT /account/{k}/status com um status inexistente -> 400 AccountStatusNotFound."""
        account_key = _create_pj_account()

        resp = ClientRequisition.send(
            "PUT",
            f"/account/{account_key}/status",
            payload={"status": "bogus", "reason_code": "VOLUNTARY"},
            headers=HEADERS,
        )
        assert resp.response_status == 400
        assert resp.response_json["code"] == "QIT002010"

    def test_invalid_operation_on_unblock_beyond_blocked_balance_qit002007(self) -> None:
        """PUT /account/{k}/blocked-balance UNBLOCK acima do bloqueado -> 422 InvalidOperation."""
        account_key = _create_pj_account()

        # A conta nasce com saldo (e bloqueio) zero, então desbloquear
        # qualquer valor é operação inválida.
        resp = ClientRequisition.send(
            "PUT",
            f"/account/{account_key}/blocked-balance",
            payload={"operation": "UNBLOCK", "amount": 5000, "reason": "sem saldo bloqueado"},
            headers=HEADERS,
        )
        assert resp.response_status == 422
        assert resp.response_json["code"] == "QIT002007"

    def test_account_blocked_for_debit_returns_409_qit002015(self) -> None:
        """Conta bloqueada não debita: bloqueia a origem e tenta transferir -> 409."""
        src_key = _create_pj_account()
        dst_key = _create_pj_account()

        # Garante saldo na origem para que a recusa seja pelo bloqueio da
        # conta, não por falta de fundos.
        cash_in = ClientRequisition.send(
            "POST",
            "/cash-in",
            payload={"account_key": src_key, "amount": 50000, "description": "Aporte"},
            headers=HEADERS,
        )
        assert cash_in.response_status == 200

        block = ClientRequisition.send(
            "PUT",
            f"/account/{src_key}/status",
            payload={"status": "blocked", "reason_code": "VOLUNTARY", "reason": "Bloqueio"},
            headers=HEADERS,
        )
        assert block.response_status == 202
        assert block.response_json["status"] == "blocked"

        resp = ClientRequisition.send(
            "POST",
            "/transfer",
            payload={
                "source_account_key": src_key,
                "destination_account_key": dst_key,
                "amount": 10000,
                "description": "Tentativa a partir de conta bloqueada",
                "transaction_pin": "1234",
            },
            headers=HEADERS,
        )
        assert resp.response_status == 409
        assert resp.response_json["code"] == "QIT002015"


class TestChargeAndCreditDomainErrors:
    def test_not_found_charge_returns_404_qit002003(self) -> None:
        """GET /charge/{uuid aleatório} -> 404 NotFoundCharge."""
        resp = ClientRequisition.send("GET", f"/charge/{uuid.uuid4()}", headers=HEADERS)
        assert resp.response_status == 404
        assert resp.response_json["code"] == "QIT002003"

    def test_not_found_credit_contract_returns_404_qit002004(self) -> None:
        """GET /credit/contract/{uuid aleatório} -> 404 NotFoundCreditContract."""
        resp = ClientRequisition.send("GET", f"/credit/contract/{uuid.uuid4()}", headers=HEADERS)
        assert resp.response_status == 404
        assert resp.response_json["code"] == "QIT002004"
