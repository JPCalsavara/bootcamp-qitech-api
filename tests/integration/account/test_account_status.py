from datetime import date
import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestAccountStatus:
    """RFC 01: Ciclo de Vida da Conta e Bloqueio Cautelar MED (Resoluções BCB 103/2021 e 518/2025)."""

    def _setup_account(self) -> str:
        import uuid
        cpf = RandomGenerator.generate_cpf()
        random_suffix = str(uuid.uuid4())[:8]
        email = f"status.{random_suffix}@exemplo.com.br"
        random_digits = f"{random.randint(1000, 9999)}"
        cnpj = f"{random.randint(10, 99)}.{random.randint(100, 999)}.{random.randint(100, 999)}/{random_digits}-90"

        payload = {
            "name": "Titular Ciclo Vida",
            "legal_name": "Titular Ciclo Vida MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1990-05-15",
            "phone": "+5511988887777",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }

        resp_customer = ClientRequisition.send(
            "POST",
            "/customers",
            payload=payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_customer.response_status == 202, f"POST /customers failed: {resp_customer.response_json}"
        customer_key = resp_customer.response_json["customer_key"]


        resp_accounts = ClientRequisition.send(
            "POST",
            f"/customers/{customer_key}/accounts",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        accounts = resp_accounts.response_json
        pj_acc = next(a for a in accounts if a["type"] == "PJ")
        return pj_acc["account_key"]

    def test_account_status_transition_active_to_blocked_and_back(self) -> None:
        account_key = self._setup_account()

        # 1. Bloqueia a conta voluntariamente
        resp_block = ClientRequisition.send(
            "PUT",
            f"/accounts/{account_key}/status",
            payload={
                "status": "blocked",
                "reason_code": "VOLUNTARY",
                "reason": "Bloqueio preventivo pelo usuário",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_block.response_status == 202
        assert resp_block.response_json["status"] == "blocked"

        # Verifica persistência da mudança
        resp_get = ClientRequisition.send("GET", f"/accounts/{account_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_get.response_json["status"] == "blocked"

        # 2. Desbloqueia a conta de volta para active
        resp_unblock = ClientRequisition.send(
            "PUT",
            f"/accounts/{account_key}/status",
            payload={
                "status": "active",
                "reason_code": "VOLUNTARY",
                "reason": "Desbloqueio solicitado pelo titular",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_unblock.response_status == 202
        assert resp_unblock.response_json["status"] == "active"

    def test_account_close_rejected_if_balance_positive(self) -> None:
        account_key = self._setup_account()

        # Adiciona saldo na conta
        resp_cashin = ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": account_key, "amount": 10000, "description": "Aporte inicial"},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_cashin.response_status == 200

        # Tenta encerrar com saldo positivo -> deve ser rejeitado com 409 (QIT001011)
        resp_close = ClientRequisition.send(
            "PUT",
            f"/accounts/{account_key}/status",
            payload={
                "status": "closed",
                "reason_code": "VOLUNTARY",
                "reason": "Encerramento de conta",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_close.response_status == 409
        assert resp_close.response_json["code"] == "QIT001011"

    def test_account_close_success_when_balance_zero_and_rejects_further_transitions(self) -> None:
        account_key = self._setup_account()

        # Encerra conta com saldo zero
        resp_close = ClientRequisition.send(
            "PUT",
            f"/accounts/{account_key}/status",
            payload={
                "status": "closed",
                "reason_code": "VOLUNTARY",
                "reason": "Encerramento sem saldo",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_close.response_status == 202
        assert resp_close.response_json["status"] == "closed"

        # Tentar alterar status a partir do estado final 'closed' deve retornar 409 (QIT001002)
        resp_reopen = ClientRequisition.send(
            "PUT",
            f"/accounts/{account_key}/status",
            payload={
                "status": "active",
                "reason_code": "VOLUNTARY",
                "reason": "Tentativa de reabertura",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_reopen.response_status == 409
        assert resp_reopen.response_json["code"] == "QIT001002"

    def test_account_forced_closure_on_compliance_fraud_even_with_balance(self) -> None:
        account_key = self._setup_account()

        # Adiciona saldo
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": account_key, "amount": 25000, "description": "Saldo ilícito suspeito"},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        # Encerramento compulsório por fraude / Resolução BCB 518/2025
        resp_force_close = ClientRequisition.send(
            "PUT",
            f"/accounts/{account_key}/status",
            payload={
                "status": "closed",
                "reason_code": "COMPLIANCE_FRAUD",
                "reason": "Irregularidade grave detectada conforme Resolução BCB 518/2025",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_force_close.response_status == 202
        assert resp_force_close.response_json["status"] == "closed"

    def test_apply_and_release_blocked_balance_cautelar_med(self) -> None:
        src_key = self._setup_account()
        dst_key = self._setup_account()

        # 1. Aporte de R$ 500,00
        resp_cashin = ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": src_key, "amount": 50000, "description": "Saldo inicial"},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_cashin.response_status == 200

        # 2. Aplica bloqueio cautelar MED de R$ 200,00 (Resolução BCB 103/2021)
        resp_block = ClientRequisition.send(
            "PUT",
            f"/accounts/{src_key}/blocked-balance",
            payload={
                "operation": "BLOCK",
                "amount": 20000,
                "reason": "Notificação de infração MED BACEN",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_block.response_status == 200
        block_data = resp_block.response_json
        assert block_data["balance"] == 50000
        assert block_data["blocked_balance"] == 20000
        assert block_data["available_balance"] == 30000

        # 3. Tenta transferir R$ 350,00 (saldo disponível é 300,00) -> deve falhar com 422
        resp_tx_fail = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload={
                "source_account_key": src_key,
                "destination_account_key": dst_key,
                "amount": 35000,
                "description": "Tentativa com saldo bloqueado",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_tx_fail.response_status == 422

        # 4. Desbloqueia R$ 200,00
        resp_unblock = ClientRequisition.send(
            "PUT",
            f"/accounts/{src_key}/blocked-balance",
            payload={
                "operation": "UNBLOCK",
                "amount": 20000,
                "reason": "MED concluído favorável ao titular",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_unblock.response_status == 200
        assert resp_unblock.response_json["blocked_balance"] == 0
        assert resp_unblock.response_json["available_balance"] == 50000

        # 5. Transferência de R$ 350,00 agora é permitida
        resp_tx_ok = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload={
                "source_account_key": src_key,
                "destination_account_key": dst_key,
                "amount": 35000,
                "description": "Transferência pós desbloqueio",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_tx_ok.response_status == 200

