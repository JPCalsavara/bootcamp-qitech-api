import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestKycOnboarding:
    """RFC 03: Onboarding Seguro & KYC Antifraude."""

    def _create_customer(self) -> str:
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"kyc.{random_digits}@exemplo.com.br"
        cnpj = f"12.345.678/{random_digits}-90"

        payload = {
            "name": "Cliente KYC",
            "legal_name": "Cliente KYC MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1988-03-12",
            "phone": "+5511988881111",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }

        resp = ClientRequisition.send(
            "POST",
            "/customers",
            payload=payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 202
        return resp.response_json["customer_key"]

    def test_kyc_approval_transitions_to_active(self) -> None:
        customer_key = self._create_customer()

        payload = {
            "score": 700,
            "risk_tier": "LOW",
            "cnd_federal_status": "REGULAR",
            "cnd_trabalhista_status": "REGULAR",
            "cadsan_status": "REGULAR",
            "flags": {},
        }
        resp = ClientRequisition.send(
            "POST",
            f"/customers/{customer_key}/kyc/analysis",
            payload=payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 200
        data = resp.response_json
        assert data["customer_status"] == "active"
        assert data["recommendation"] == "APPROVE"

        # Confirma via GET /customers/{customer_key}
        resp_get = ClientRequisition.send(
            "GET",
            f"/customers/{customer_key}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_get.response_status == 200
        assert resp_get.response_json["status"] == "active"

    def test_kyc_rejection_on_low_score(self) -> None:
        customer_key = self._create_customer()

        payload = {
            "score": 250,
            "risk_tier": "HIGH",
            "cnd_federal_status": "IRREGULAR",
            "cnd_trabalhista_status": "REGULAR",
            "cadsan_status": "IRREGULAR",
            "flags": {"sanctioned": True},
        }
        resp = ClientRequisition.send(
            "POST",
            f"/customers/{customer_key}/kyc/analysis",
            payload=payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 200
        data = resp.response_json
        assert data["customer_status"] == "rejected"
        assert data["recommendation"] == "REJECT"

    def test_kyc_under_review_on_medium_score(self) -> None:
        customer_key = self._create_customer()

        payload = {
            "score": 450,
            "risk_tier": "MEDIUM",
            "cnd_federal_status": "REGULAR",
            "cnd_trabalhista_status": "PENDING",
            "cadsan_status": "REGULAR",
            "flags": {},
        }
        resp = ClientRequisition.send(
            "POST",
            f"/customers/{customer_key}/kyc/analysis",
            payload=payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 200
        data = resp.response_json
        assert data["customer_status"] == "under_review"
        assert data["recommendation"] == "MANUAL_REVIEW"

    def test_kyc_analysis_fetches_from_kyc_connector_when_payload_empty(self) -> None:
        customer_key = self._create_customer()

        # Chamada sem score no payload -> deve acionar o KycConnector
        resp = ClientRequisition.send(
            "POST",
            f"/customers/{customer_key}/kyc/analysis",
            payload={},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 200
        data = resp.response_json
        assert "score" in data and data["score"] > 0
        assert data["customer_status"] in ("active", "under_review", "rejected")
        assert "risk_tier" in data

