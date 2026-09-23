import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestE2EComplianceFraudAndClosure:
    """Jornada E2E 2: Risco, Bloqueio Cautelar MED (Bacen), Evasão de Fraude e Encerramento Compulsório/Voluntário.

    Cobre:
    - RFC 01: Ciclo de Vida da Conta e Bloqueio Cautelar MED (Resoluções BCB 103/2021 e 518/2025)
    - ADR-0007: Máquina de estados com tabela de domínio e regra de saldo residual zero para encerramento voluntário
    - ADR-0002: Trava de concorrência e saldo disponível
    """

    def _setup_customer_and_accounts(self, name: str) -> tuple[str, str, str]:
        cpf = RandomGenerator.generate_cpf()
        random_suffix = f"{random.randint(10000, 99999)}"
        email = f"compliance_{random_suffix}@exemplo.com.br"
        cnpj = f"12.345.678/{random.randint(1000, 9999)}-90"

        payload = {
            "name": name,
            "legal_name": f"{name} MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1991-07-20",
            "phone": "+5511977776666",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }

        # 1. Onboarding
        resp_cust = ClientRequisition.send("POST", "/customers", payload=payload, headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_cust.response_status == 202
        customer_key = resp_cust.response_json["customer_key"]

        # 2. Aprovação KYC
        resp_kyc = ClientRequisition.send(
            "POST",
            f"/customers/{customer_key}/kyc/analysis",
            payload={"score": 800, "risk_tier": "LOW", "flags": {"pep": False, "sanctions": False}},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_kyc.response_status == 200

        # 3. Provisionamento de contas gêmeas PF/PJ
        resp_acc = ClientRequisition.send(
            "POST",
            f"/customers/{customer_key}/accounts",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_acc.response_status == 201
        accounts = resp_acc.response_json
        pj_acc = next(a for a in accounts if a["type"] == "PJ")
        pf_acc = next(a for a in accounts if a["type"] == "PF")
        return customer_key, pj_acc["account_key"], pf_acc["account_key"]

    def test_e2e_journey_compliance_fraud_med_and_forced_closure(self) -> None:
        """Cenário 1: Notificação de infração MED, tentativa de evasão barrada e encerramento compulsório por fraude."""
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts("Suspeito Fraude")

        # 1. Aporte / Venda Pix de R$ 5.000,00 na conta PJ
        resp_cashin = ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": pj_key, "amount": 500000, "description": "Venda Pix suspeita"},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_cashin.response_status == 200

        # 2. Notificação de Infração Bacen / Bloqueio Cautelar MED de R$ 4.000,00
        resp_med = ClientRequisition.send(
            "PUT",
            f"/accounts/{pj_key}/blocked-balance",
            payload={
                "operation": "BLOCK",
                "amount": 400000,
                "reason": "Notificação de infração MED BACEN - Resolução 103/2021",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_med.response_status == 200
        assert resp_med.response_json["balance"] == 500000
        assert resp_med.response_json["blocked_balance"] == 400000
        assert resp_med.response_json["available_balance"] == 100000

        # 3. Tentativa de Evasão de Fraude: Usuário tenta transferir R$ 2.000,00
        # Deve ser bloqueado porque o saldo disponível livre é de apenas R$ 1.000,00
        resp_transfer_fail = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload={
                "source_account_key": pj_key,
                "destination_account_key": pf_key,
                "amount": 200000,
                "description": "Tentativa de esvaziamento de fundos",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_transfer_fail.response_status == 422
        assert resp_transfer_fail.response_json["code"] == "QIT002005"

        # 4. Transferência legítima dentro do saldo disponível (R$ 500,00) deve passar
        resp_transfer_ok = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload={
                "source_account_key": pj_key,
                "destination_account_key": pf_key,
                "amount": 50000,
                "description": "Retirada permitida dentro da margem livre",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_transfer_ok.response_status == 200

        # 5. Investigação de Compliance confirma fraude grave
        # Encerramento compulsório da conta por fraude (Resolução BCB 518/2025, ADR-0007)
        # Permite fechamento imediato mesmo com saldo residual
        resp_force_close = ClientRequisition.send(
            "PUT",
            f"/accounts/{pj_key}/status",
            payload={
                "status": "closed",
                "reason_code": "COMPLIANCE_FRAUD",
                "reason": "Irregularidade grave e fraude confirmada conforme Resolução BCB 518/2025",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_force_close.response_status == 202
        assert resp_force_close.response_json["status"] == "closed"

        # 6. Tentar reabrir conta encerrada por fraude é proibido (409)
        resp_reopen = ClientRequisition.send(
            "PUT",
            f"/accounts/{pj_key}/status",
            payload={
                "status": "active",
                "reason_code": "VOLUNTARY",
                "reason": "Tentativa indevida de reativação",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_reopen.response_status == 409
        assert resp_reopen.response_json["code"] == "QIT001002"

    def test_e2e_journey_voluntary_offboarding_residual_balance_barrier(self) -> None:
        """Cenário 2: Offboarding voluntário - Barreira de saldo positivo e encerramento após zerar conta."""
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts("Cliente Regular")

        # 1. Conta acumula saldo comercial de R$ 1.500,00
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": pj_key, "amount": 150000, "description": "Faturamento Comercial"},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        # 2. Cliente tenta encerrar a conta com saldo positivo -> Rejeitado (409 ADR-0007)
        resp_close_fail = ClientRequisition.send(
            "PUT",
            f"/accounts/{pj_key}/status",
            payload={
                "status": "closed",
                "reason_code": "VOLUNTARY",
                "reason": "Cliente solicitou encerramento via app",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_close_fail.response_status == 409
        assert resp_close_fail.response_json["code"] == "QIT001011"

        # 3. Cliente resgata todo o saldo transferindo para a conta PF (R$ 1.500,00)
        resp_transfer = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload={
                "source_account_key": pj_key,
                "destination_account_key": pf_key,
                "amount": 150000,
                "description": "Zerar saldo para encerramento de conta",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_transfer.response_status == 200

        # Verifica saldo zerado na PJ
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 0

        # 4. Agora a solicitação de encerramento voluntário é aceita!
        resp_close_ok = ClientRequisition.send(
            "PUT",
            f"/accounts/{pj_key}/status",
            payload={
                "status": "closed",
                "reason_code": "VOLUNTARY",
                "reason": "Conta zerada, encerramento concluído",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_close_ok.response_status == 202
        assert resp_close_ok.response_json["status"] == "closed"
