from datetime import datetime
import os
from typing import Any, Dict, Optional

from connectors.rest_connector import RestConnector


class PaymentConnector(RestConnector):
    """Conector HTTP de saída para Gateway de Pagamentos e Compensação Bancária (RFC 04).

    Em produção, comunica-se com SPI/DICT (PIX), CIP/Nuclea (Boleto) e Adquirente via HTTP de saída.
    Em ambiente local/testes (MOCK_EXTERNAL_SERVICES=true ou localhost), executa simulação determinística.
    Suporta reconciliação ativa (polling de saída) para boletos e pagamentos não instantâneos.
    """

    def __init__(self) -> None:
        base_url = os.environ.get("PAYMENT_GATEWAY_URL", "http://localhost:8080/payments")
        timeout = int(os.environ.get("PAYMENT_GATEWAY_TIMEOUT", "5"))
        internal_token = os.environ.get("PAYMENT_GATEWAY_TOKEN", "payment_token")
        super().__init__(class_name=__name__, base_url=base_url, timeout=timeout, internal_token=internal_token)
        self.mock_mode = os.environ.get("MOCK_EXTERNAL_SERVICES", "true").lower() == "true" or "localhost" in base_url

    def create_charge(
        self,
        method: str,
        amount: int,
        due_date: str,
        customer_document: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Solicita registro da cobrança na câmara de compensação / gateway externo."""
        if self.mock_mode:
            return {
                "status": "REGISTERED",
                "external_id": f"EXT-{method}-{amount}",
                "registered_at": datetime.now().isoformat(),
            }
        resp = self.send(
            "/charges",
            "POST",
            payload={
                "method": method,
                "amount": amount,
                "due_date": due_date,
                "customer_document": customer_document,
            },
        )
        return resp.response_json or {}

    def check_charge_status(self, charge_key: str, method: Optional[str] = None) -> Dict[str, Any]:
        """Consulta o status de liquidação de uma cobrança junto ao parceiro/banco."""
        if self.mock_mode:
            # Em modo mock para testes de integração, simula que a cobrança foi compensada no banco parceiro
            return {
                "charge_key": charge_key,
                "status": "PAID",
                "paid_at": datetime.now().isoformat(),
                "method": method or "BOLETO",
            }
        resp = self.send(f"/charges/{charge_key}/status", "GET")
        return resp.response_json or {}
