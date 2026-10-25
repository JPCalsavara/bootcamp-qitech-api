"""COD-03 (continuação): os dois erros de serviço externo que só existem
quando o connector faz HTTP de verdade — QIT002013 ExternalServiceTimeout (504)
e QIT002014 ExternalServiceUnavailable (502).

Dependem do MockServer da FEAT-005: a API roda com MOCK_EXTERNAL_SERVICES=false
e os connectors apontam para http://mockserver:1080, logo saem do modo simulado
e batem no mock. Provocamos cada falha instruindo o MockServer a:
  - atrasar a resposta além do timeout do connector (5s) -> RestConnector levanta
    ExternalServiceTimeout -> 504 QIT002013;
  - derrubar a conexão (httpError dropConnection) -> ExternalServiceUnavailable
    -> 502 QIT002014.

Caixa-preta (ADR-0001): fala com a API por HTTP e com o MockServer pela API HTTP
dele (porta MOCKSERVER_PORT). Não importa de src nem acessa o banco.
"""

from datetime import date, timedelta
from os import environ
import time
import uuid

import requests

from tests.utils import ClientRequisition, RandomGenerator
from tests.utils import INTERNAL_TOKEN


HEADERS = {"INTERNAL-TOKEN": INTERNAL_TOKEN}


def _mockserver_base_url() -> str:
    host = environ.get("SERVER_LOCALHOST", "0.0.0.0")
    port = environ.get("MOCKSERVER_PORT", "1080")
    return f"http://{host}:{port}"


MOCKSERVER_URL = _mockserver_base_url()

# Timeout dos connectors no docker-compose.yml é 5s; o atraso precisa passar
# disso para o requests levantar Timeout. 7s dá folga sem alongar demais.
CONNECTOR_TIMEOUT_S = int(environ.get("KYC_API_TIMEOUT", "5"))
DELAY_OVER_TIMEOUT_S = CONNECTOR_TIMEOUT_S + 2

# Baseline de expectations saudáveis (as mesmas 5 pontas da FEAT-005). O
# setup prima isto para deixar o mock num estado conhecido; cada teste
# sobrepõe a ponta que lhe interessa com priority alta e, ao final, restaura.
BASELINE_EXPECTATIONS = [
    {
        "httpRequest": {"method": "GET", "path": "/kyc"},
        "httpResponse": {"statusCode": 200, "body": {"service": "kyc-bureau", "status": "UP"}},
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
        "httpResponse": {"statusCode": 200, "body": {"service": "payment-gateway", "status": "UP"}},
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
        "httpRequest": {"method": "GET", "path": "/payments/charges/[^/]+/status"},
        "httpResponse": {
            "statusCode": 200,
            "headers": {"content-type": ["application/json"]},
            "body": {"status": "PAID"},
        },
    },
]


def _wait_for_mockserver(timeout_s: int = 30) -> None:
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


def _prime_baseline() -> None:
    requests.put(f"{MOCKSERVER_URL}/mockserver/reset", timeout=5).raise_for_status()
    for expectation in BASELINE_EXPECTATIONS:
        resp = requests.put(f"{MOCKSERVER_URL}/mockserver/expectation", json=expectation, timeout=5)
        assert resp.status_code in (200, 201), f"falha ao primar baseline: {resp.status_code} {resp.text}"


def _override(expectation: dict) -> None:
    """Sobrepõe uma ponta com priority alta para que o override vença o baseline."""
    resp = requests.put(f"{MOCKSERVER_URL}/mockserver/expectation", json=expectation, timeout=5)
    assert resp.status_code in (200, 201), f"falha ao sobrepor expectation: {resp.status_code} {resp.text}"


def _create_customer() -> str:
    random_suffix = str(uuid.uuid4())[:8]
    payload = {
        "name": "Cliente Externo",
        "legal_name": "Cliente Externo MEI LTDA",
        "email": f"externo.{random_suffix}@exemplo.com.br",
        "cpf": RandomGenerator.generate_cpf(),
        "cnpj": RandomGenerator.generate_cnpj(),
        "birthdate": "1990-01-01",
        "phone": "+5511977771111",
        "password": "SenhaForte@2026",
        "transaction_pin": "1234",
    }
    resp = ClientRequisition.send("POST", "/customer", payload=payload, headers=HEADERS)
    assert resp.response_status == 202, resp.response_json
    return resp.response_json["customer_key"]


def _create_pj_account() -> str:
    customer_key = _create_customer()
    resp = ClientRequisition.send("POST", f"/customer/{customer_key}/account", headers=HEADERS)
    assert resp.response_status == 201, resp.response_json
    return next(a for a in resp.response_json if a["type"] == "PJ")["account_key"]


class TestExternalServiceErrors:
    @classmethod
    def setup_class(cls) -> None:
        _wait_for_mockserver()
        _prime_baseline()

    @classmethod
    def teardown_class(cls) -> None:
        # Restaura o mock para um estado saudável, para não quebrar testes
        # de connector que porventura rodem depois nesta mesma suíte.
        _prime_baseline()

    def test_kyc_timeout_returns_504_qit002013(self) -> None:
        """KYC /kyc/analyze atrasado além do timeout -> 504 ExternalServiceTimeout."""
        _override(
            {
                "priority": 10,
                "httpRequest": {"method": "POST", "path": "/kyc/analyze"},
                "httpResponse": {
                    "statusCode": 200,
                    "body": {"score": 780, "recommendation": "APPROVE"},
                    "delay": {"timeUnit": "SECONDS", "value": DELAY_OVER_TIMEOUT_S},
                },
            }
        )
        try:
            customer_key = _create_customer()
            resp = ClientRequisition.send(
                "POST",
                f"/customer/{customer_key}/kyc/analysis",
                payload={},
                headers=HEADERS,
            )
            assert resp.response_status == 504
            assert resp.response_json["code"] == "QIT002013"
        finally:
            _prime_baseline()

    def test_payment_unavailable_returns_502_qit002014(self) -> None:
        """Gateway de pagamento com conexão derrubada -> 502 ExternalServiceUnavailable."""
        pj_key = _create_pj_account()
        due_date = (date.today() + timedelta(days=7)).isoformat()

        resp_charge = ClientRequisition.send(
            "POST",
            f"/account/{pj_key}/charge",
            payload={"method": "BOLETO", "amount": 30000, "due_date": due_date},
            headers=HEADERS,
        )
        assert resp_charge.response_status == 201
        charge_key = resp_charge.response_json["charge_key"]

        # A reconciliação faz GET /payments/charges/{key}/status; derrubar a
        # conexão nessa ponta faz o RestConnector levantar ExternalServiceUnavailable.
        _override(
            {
                "priority": 10,
                "httpRequest": {"method": "GET", "path": "/payments/charges/[^/]+/status"},
                "httpError": {"dropConnection": True},
            }
        )
        try:
            resp = ClientRequisition.send(
                "POST",
                "/charge/reconciliation",
                payload={"charge_keys": [charge_key]},
                headers=HEADERS,
            )
            assert resp.response_status == 502
            assert resp.response_json["code"] == "QIT002014"
        finally:
            _prime_baseline()
