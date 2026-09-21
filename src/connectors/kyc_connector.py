import os
from typing import Any, Dict

from connectors.rest_connector import BaseConnectorResponse, RestConnector


class KycConnector(RestConnector):
    """Conector HTTP de saída para Bureau de Crédito (Serasa/Boa Vista) e Antifraude (RFC 03).

    Em ambiente de produção, consome a API externa do bureau via HTTP de saída (egress-only).
    Em ambiente local/testes (MOCK_EXTERNAL_SERVICES=true ou sem URL externa configurada),
    executa simulação determinística realista baseada no documento.
    """

    def __init__(self) -> None:
        base_url = os.environ.get("KYC_API_URL", "http://localhost:8080/kyc")
        timeout = int(os.environ.get("KYC_API_TIMEOUT", "5"))
        internal_token = os.environ.get("KYC_API_TOKEN", "default_token")
        super().__init__(class_name=__name__, base_url=base_url, timeout=timeout, internal_token=internal_token)
        self.mock_mode = os.environ.get("MOCK_EXTERNAL_SERVICES", "true").lower() == "true" or "localhost" in base_url

    def analyze_document(self, cpf: str, cnpj: str) -> Dict[str, Any]:
        """Consulta o score e situação cadastral do cliente no Bureau."""
        if self.mock_mode:
            clean_cpf = "".join(filter(str.isdigit, cpf))
            last_digit = int(clean_cpf[-1]) if clean_cpf else 5

            if last_digit == 0:
                # Cenário de alto risco / reprovação
                return {
                    "score": 250,
                    "risk_tier": "HIGH",
                    "cnd_federal_status": "IRREGULAR",
                    "cnd_trabalhista_status": "REGULAR",
                    "cadsan_status": "IRREGULAR",
                    "flags": {"sanctioned": True},
                    "recommendation": "REJECT",
                }
            elif last_digit % 2 == 0:
                # Cenário de médio risco / análise manual
                return {
                    "score": 480,
                    "risk_tier": "MEDIUM",
                    "cnd_federal_status": "REGULAR",
                    "cnd_trabalhista_status": "PENDING",
                    "cadsan_status": "REGULAR",
                    "flags": {},
                    "recommendation": "MANUAL_REVIEW",
                }
            else:
                # Cenário de baixo risco / aprovação imediata
                return {
                    "score": 780,
                    "risk_tier": "LOW",
                    "cnd_federal_status": "REGULAR",
                    "cnd_trabalhista_status": "REGULAR",
                    "cadsan_status": "REGULAR",
                    "flags": {"pep": False, "sanctions": False},
                    "recommendation": "APPROVE",
                }

        # Chamada real ao parceiro
        payload = {"cpf": cpf, "cnpj": cnpj}
        response: BaseConnectorResponse = self.send(endpoint="/analyze", method="POST", payload=payload)
        return response.response_json or {}
