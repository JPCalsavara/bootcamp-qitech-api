"""COD-13: verifica que os connectors de saída (KYC e gateway de pagamento)
fazem HTTP de verdade contra um MockServer controlável.

Pré-condição de ambiente (docker-compose.yml):
  - a API roda com MOCK_EXTERNAL_SERVICES=false, KYC_API_URL=http://mockserver:1080/kyc
    e PAYMENT_GATEWAY_URL=http://mockserver:1080/payments. Como a URL não é
    localhost e o mock está desligado, os connectors saem do modo simulado e
    batem no MockServer de verdade.

Estes testes são caixa-preta (ADR-0001): falam com a API sobre HTTP e com o
MockServer sobre a API HTTP dele (porta MOCKSERVER_PORT). Não importam de src
nem acessam o banco.

Fluxo de cada teste:
  1. limpa os pedidos já gravados no mock (PUT /mockserver/clear ... type=LOG);
  2. dispara a rota da API que aciona o connector;
  3. confere, pela API de verificação do mock (PUT /mockserver/verify), que o
     pedido esperado chegou com método, path e corpo certos.
"""

from datetime import date, timedelta
from os import environ
import random
import time

import requests

from tests.utils import ClientRequisition, RandomGenerator
from tests.utils import INTERNAL_TOKEN


def _mockserver_base_url() -> str:
    host = environ.get("SERVER_LOCALHOST", "0.0.0.0")
    port = environ.get("MOCKSERVER_PORT", "1080")
    return f"http://{host}:{port}"


MOCKSERVER_URL = _mockserver_base_url()

# As 5 "pontas" do contrato externo. As três primeiras são as que os connectors
# realmente chamam (KycConnector.analyze_document, PaymentConnector.create_charge
# e PaymentConnector.check_charge_status); GET /kyc e GET /payments completam o
# contrato do serviço externo e são primadas por consistência.
EXPECTATIONS = [
    {
        "httpRequest": {"method": "GET", "path": "/kyc"},
        "httpResponse": {
            "statusCode": 200,
            "headers": {"content-type": ["application/json"]},
            "body": {"service": "kyc-bureau", "status": "UP"},
        },
    },
    {
        "httpRequest": {"method": "POST", "path": "/kyc/analyze"},
        "httpResponse": {
            "statusCode": 200,
            "headers": {"content-type": ["application/json"]},
            "body": {
                "score": 780,
                "risk_tier": "LOW",
                "cnd_federal_status": "REGULAR",
                "cnd_trabalhista_status": "REGULAR",
                "cadsan_status": "REGULAR",
                "flags": {"pep": False, "sanctions": False},
                "recommendation": "APPROVE",
            },
        },
    },
    {
        "httpRequest": {"method": "GET", "path": "/payments"},
        "httpResponse": {
            "statusCode": 200,
            "headers": {"content-type": ["application/json"]},
            "body": {"service": "payment-gateway", "status": "UP"},
        },
    },
    {
        "httpRequest": {"method": "POST", "path": "/payments/charges"},
        "httpResponse": {
            "statusCode": 200,
            "headers": {"content-type": ["application/json"]},
            "body": {"status": "REGISTERED", "external_id": "EXT-MOCK-1"},
        },
    },
    {
        # path tratado como regex pelo MockServer: casa com qualquer charge_key.
        "httpRequest": {"method": "GET", "path": "/payments/charges/[^/]+/status"},
        "httpResponse": {
            "statusCode": 200,
            "headers": {"content-type": ["application/json"]},
            "body": {"status": "PAID"},
        },
    },
]


def _wait_for_mockserver(timeout_s: int = 30) -> None:
    """Espera o MockServer responder — a imagem não tem shell pra healthcheck
    de container, então quem confirma que ele subiu é este teste."""
    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        try:
            resp = requests.put(f"{MOCKSERVER_URL}/mockserver/status", timeout=3)
            if resp.status_code in (200, 201):
                return
        except requests.exceptions.RequestException as ex:
            last_error = ex
        time.sleep(1)
    raise RuntimeError(
        f"MockServer não respondeu em {MOCKSERVER_URL} dentro de {timeout_s}s. "
        f"Suba o ambiente com `docker compose up -d --build`. Último erro: {last_error}"
    )


def _prime_expectations() -> None:
    requests.put(f"{MOCKSERVER_URL}/mockserver/reset", timeout=5).raise_for_status()
    for expectation in EXPECTATIONS:
        resp = requests.put(f"{MOCKSERVER_URL}/mockserver/expectation", json=expectation, timeout=5)
        assert resp.status_code in (200, 201), f"falha ao primar expectation: {resp.status_code} {resp.text}"


def _clear_recorded_requests() -> None:
    """Zera só o log de pedidos recebidos, mantendo as expectations primadas."""
    resp = requests.put(f"{MOCKSERVER_URL}/mockserver/clear?type=LOG", timeout=5)
    assert resp.status_code in (200, 201)


def _recorded_body(recorded_request: dict) -> dict:
    """Extrai o JSON do corpo de um pedido gravado no MockServer. Dependendo
    da versão/formato, o corpo vem como {"type":"JSON","json":{...}} ou já
    como o próprio objeto."""
    body = recorded_request.get("body")
    if isinstance(body, dict):
        if "json" in body:
            return body["json"]
        if body.get("type") == "JSON" and isinstance(body.get("value"), dict):
            return body["value"]
        return body
    return {}


def _verify(request_matcher: dict, at_least: int = 1) -> None:
    """Confere via API de verificação do MockServer que um pedido casando com
    request_matcher chegou pelo menos `at_least` vez(es). O mock responde 202
    quando a verificação passa e 406 quando falha (com o detalhe no corpo)."""
    body = {"httpRequest": request_matcher, "times": {"atLeast": at_least}}
    resp = requests.put(f"{MOCKSERVER_URL}/mockserver/verify", json=body, timeout=5)
    assert resp.status_code == 202, f"verificação falhou para {request_matcher}: {resp.text}"


class TestConnectorsOverMockServer:
    """COD-13: cada chamada de connector chega ao MockServer com rota e payload certos."""

    @classmethod
    def setup_class(cls) -> None:
        _wait_for_mockserver()
        _prime_expectations()

    def _create_customer(self) -> str:
        random_digits = f"{random.randint(1000, 9999)}"
        payload = {
            "name": "Cliente Connector",
            "legal_name": "Cliente Connector MEI LTDA",
            "email": f"connector.{random_digits}@exemplo.com.br",
            "cpf": RandomGenerator.generate_cpf(),
            "cnpj": RandomGenerator.generate_cnpj(),
            "birthdate": "1990-01-01",
            "phone": "+5511977772222",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }
        resp = ClientRequisition.send("POST", "/customer", payload=payload, headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp.response_status == 202
        return resp.response_json["customer_key"]

    def _setup_pj_account(self) -> str:
        customer_key = self._create_customer()
        resp = ClientRequisition.send(
            "POST",
            f"/customer/{customer_key}/account",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        accounts = resp.response_json
        return next(a for a in accounts if a["type"] == "PJ")["account_key"]

    def test_kyc_analyze_calls_mockserver_with_expected_route_and_payload(self) -> None:
        """POST /customer/{k}/kyc/analysis com corpo vazio -> KycConnector POST /kyc/analyze."""
        _clear_recorded_requests()
        customer_key = self._create_customer()

        resp = ClientRequisition.send(
            "POST",
            f"/customer/{customer_key}/kyc/analysis",
            payload={},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 200
        # A resposta primada no mock (score 780 / APPROVE) é a que a API devolve.
        assert resp.response_json["score"] == 780
        assert resp.response_json["recommendation"] == "APPROVE"

        # Rota e método certos.
        _verify({"method": "POST", "path": "/kyc/analyze"})

        # E o corpo enviado carrega cpf e cnpj (o que KycConnector monta). Os
        # valores são gerados por cliente, então conferimos a FORMA do payload,
        # não valores fixos: busca os pedidos gravados e inspeciona o JSON.
        recorded = requests.put(
            f"{MOCKSERVER_URL}/mockserver/retrieve?type=REQUESTS&format=JSON",
            json={"method": "POST", "path": "/kyc/analyze"},
            timeout=5,
        )
        assert recorded.status_code == 200
        received = recorded.json()
        assert received, "nenhum pedido POST /kyc/analyze foi gravado no MockServer"
        bodies = [_recorded_body(r) for r in received]
        assert any(
            isinstance(b, dict) and b.get("cpf") and b.get("cnpj") for b in bodies
        ), f"corpo recebido não tem cpf/cnpj: {received}"

    def test_payment_create_charge_calls_mockserver_with_expected_route_and_payload(self) -> None:
        """POST /account/{k}/charge -> PaymentConnector POST /payments/charges."""
        _clear_recorded_requests()
        pj_key = self._setup_pj_account()
        due_date = (date.today() + timedelta(days=7)).isoformat()

        resp = ClientRequisition.send(
            "POST",
            f"/account/{pj_key}/charge",
            payload={"method": "BOLETO", "amount": 25000, "due_date": due_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 201

        _verify(
            {
                "method": "POST",
                "path": "/payments/charges",
                "body": {
                    "type": "JSON",
                    "json": {"method": "BOLETO", "amount": 25000, "due_date": due_date},
                    "matchType": "ONLY_MATCHING_FIELDS",
                },
            }
        )

    def test_payment_check_status_calls_mockserver_with_expected_route(self) -> None:
        """POST /charge/reconciliation -> PaymentConnector GET /payments/charges/{key}/status."""
        _clear_recorded_requests()
        pj_key = self._setup_pj_account()
        due_date = (date.today() + timedelta(days=7)).isoformat()

        resp_charge = ClientRequisition.send(
            "POST",
            f"/account/{pj_key}/charge",
            payload={"method": "BOLETO", "amount": 30000, "due_date": due_date},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_charge.response_status == 201
        charge_key = resp_charge.response_json["charge_key"]

        resp_rec = ClientRequisition.send(
            "POST",
            "/charge/reconciliation",
            payload={"charge_keys": [charge_key]},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_rec.response_status == 200
        # Status PAID primado no mock -> a cobrança é liquidada.
        assert resp_rec.response_json["reconciled_count"] >= 1

        _verify(
            {
                "method": "GET",
                "path": f"/payments/charges/{charge_key}/status",
            }
        )
