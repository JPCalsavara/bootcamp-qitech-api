import random
import uuid
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestCustomerCreate:
    def test_creates_customer_with_status_created_returns_202(self):
        """RFC 03 / ADR-0007: Onboarding Seguro inicia com status 'created' e responde 202 Accepted.
        
        O endpoint POST /customers recebe os dados unificados do MEI e do titular,
        valida o payload e insere o cliente com status inicial 'created'.
        """
        cpf = RandomGenerator.generate_cpf()
        random_suffix = str(uuid.uuid4())[:8]
        email = f"maria.{random_suffix}@exemplo.com.br"
        random_digits = f"{random.randint(1000, 9999)}"
        cnpj = f"12.345.678/{random_digits}-90"

        payload = {
            "name": "Maria da Silva",
            "legal_name": "Maria da Silva 12345678000190",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1990-05-17",
            "phone": "(11) 99999-8888",
            "password": "SenhaSegura123!",
            "transaction_pin": "1234",
        }

        response = ClientRequisition.send(
            "POST",
            "/customers",
            payload=payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        assert response.response_status == 202
        body = response.response_json
        assert "customer_key" in body
        assert len(body["customer_key"]) == 36
        assert body["status"] == "created"
        assert body["name"] == payload["name"]
        assert body["email"] == payload["email"]
        assert body["cpf"] == payload["cpf"]
        assert body["cnpj"] == payload["cnpj"]
