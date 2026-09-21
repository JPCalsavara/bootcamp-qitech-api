import hashlib
import hmac
import json
import random
from datetime import date, timedelta
from typing import Any, Dict, Optional, Tuple

from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


def post(endpoint: str, payload: Optional[dict] = None, headers: Optional[dict] = None) -> Tuple[int, Any]:
    h = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
    if headers:
        h.update(headers)
    resp = ClientRequisition.send("POST", endpoint, payload=payload, headers=h)
    return resp.response_status, resp.response_json


def get(endpoint: str, headers: Optional[dict] = None) -> Tuple[int, Any]:
    h = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
    if headers:
        h.update(headers)
    resp = ClientRequisition.send("GET", endpoint, headers=h)
    return resp.response_status, resp.response_json


class TestFullMeiLifecycle:
    """Teste de integração ponta a ponta que exercita a jornada completa do MEI

    cobrindo todos os requisitos das RFCs 01 a 07:
    1. Onboarding & KYC Antifraude (RFC 01 & RFC 03)
    2. Provisionamento de Contas Gêmeas PF e PJ (RFC 01)
    3. Governança e Caixinhas (Pockets) (RFC 07)
    4. Cobrança PIX e Liquidação Bruta + Tarifa Atômica (RFC 04, ADR-0008)
    5. Contratação de Crédito CCB com Trava de Recebíveis (RFC 05)
    6. Rendimento Automático de Fluxo de Caixa CDB 100% CDI (RFC 06)
    7. Governança Patrimonial e Distribuição de Lucros PJ -> PF (RFC 07, RFC 02)
    8. Auditoria de Partidas Dobradas no Ledger (RFC 02, ADR-0004)
    """

    WEBHOOK_SECRET = "qitech_bootcamp_secret_2026"

    def test_full_mei_lifecycle_journey(self) -> None:
        # =========================================================================
        # 1. Onboarding & KYC Antifraude (RFC 01 & RFC 03)
        # =========================================================================
        cpf = RandomGenerator.generate_cpf()
        random_suffix = f"{random.randint(10000, 99999)}"
        email = f"mei_{random_suffix}@exemplo.com.br"
        cnpj = f"12.345.678/{random.randint(1000, 9999)}-90"

        customer_payload = {
            "name": "Maria MEI Empreendedora",
            "legal_name": "Maria MEI Servicos Digitais LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1990-05-15",
            "phone": "+5511988887777",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }

        status_code, customer_data = post("/customers", payload=customer_payload)
        assert status_code == 202
        customer_key = customer_data["customer_key"]
        assert customer_data["status"] == "created"

        # Análise KYC automática (Score alto -> Aprova e ativa)
        kyc_payload = {
            "score": 750,
            "risk_tier": "LOW",
            "cnd_federal_status": "REGULAR",
            "cnd_trabalhista_status": "REGULAR",
            "cadsan_status": "REGULAR",
            "flags": {"pep": False, "sanctions": False},
        }
        status_code, kyc_data = post(f"/customers/{customer_key}/kyc/analysis", payload=kyc_payload)
        assert status_code == 200
        assert kyc_data["customer_status"] == "active"
        assert kyc_data["recommendation"] == "APPROVE"

        # =========================================================================
        # 2. Provisionamento de Contas Gêmeas PF e PJ (RFC 01)
        # =========================================================================
        status_code, accounts = post(f"/customers/{customer_key}/accounts")
        assert status_code == 201
        assert len(accounts) == 2

        pj_acc = next(a for a in accounts if a["type"] == "PJ")
        pf_acc = next(a for a in accounts if a["type"] == "PF")
        pj_key = pj_acc["account_key"]
        pf_key = pf_acc["account_key"]
        assert pj_acc["balance"] == 0
        assert pf_acc["balance"] == 0

        # =========================================================================
        # 3. Governança e Caixinhas (Pockets) (RFC 07)
        # =========================================================================
        # Cria caixinha de reserva prioritária do DAS-MEI
        status_code, das_pocket = post(
            f"/accounts/{pj_key}/pockets",
            payload={
                "type": "DAS_IMPOSTOS",
                "name": "Reserva Mensal DAS",
                "target_amount": 7500,  # R$ 75,00
                "is_locked": False,
            },
        )
        assert status_code == 201
        assert das_pocket["target_amount"] == 7500

        # Configura política de transferência PJ -> PF com checagem de reserva do DAS
        status_code, policy = post(
            "/governance/transfer-policies",
            payload={
                "account_pj_key": pj_key,
                "account_pf_key": pf_key,
                "max_daily_transfer_amount": 500000,  # R$ 5.000,00
                "require_pro_labore_approval": True,
                "das_reserved_check": True,
            },
        )
        assert status_code == 201

        # =========================================================================
        # 4. Cobrança PIX e Liquidação Bruta + Tarifa Atômica (RFC 04, ADR-0008)
        # =========================================================================
        due_date = (date.today() + timedelta(days=5)).isoformat()
        status_code, charge_data = post(
            f"/accounts/{pj_key}/charges",
            payload={
                "method": "PIX",
                "amount": 150000,  # R$ 1.500,00
                "due_date": due_date,
                "customer_document": "12345678909",
            },
        )
        assert status_code == 201
        charge_key = charge_data["charge_key"]
        assert charge_data["fee_amount"] == 90  # R$ 0,90
        assert charge_data["net_amount"] == 149910

        # Webhook com assinatura HMAC
        webhook_payload = {
            "event": "payment.settled",
            "charge_key": charge_key,
            "amount": 150000,
        }
        payload_bytes = json.dumps(webhook_payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(self.WEBHOOK_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

        status_code, wh_res = post(
            "/webhooks/payments",
            payload=webhook_payload,
            headers={"X-Signature-SHA256": signature},
        )
        assert status_code == 200

        # Verifica saldo da conta PJ: 150000 - 90 = 149910
        status_code, bal_data = get(f"/accounts/{pj_key}/balance")
        assert status_code == 200
        assert bal_data["balance"] == 149910

        # Verifica Revenue Tracker MEI acumulado
        status_code, tracker = get(f"/customers/{customer_key}/revenue-tracker")
        assert status_code == 200
        assert tracker["accumulated_revenue"] == 150000

        # =========================================================================
        # 5. Contratação de Crédito CCB com Trava de Recebíveis (RFC 05)
        # =========================================================================
        status_code, credit_data = post(
            "/credit/contracts",
            payload={
                "customer_key": customer_key,
                "account_pj_key": pj_key,
                "account_pf_key": pf_key,
                "requested_amount": 1000000,  # R$ 10.000,00
                "term_months": 12,
                "interest_rate_monthly": 0.0199,
                "retention_percentage": 10.0,  # 10% de trava
            },
        )
        assert status_code == 201
        assert credit_data["status"] == "disbursed"
        assert len(credit_data["installments"]) == 12
        assert credit_data["pocket_key"] is not None

        # Saldo PJ agora inclui os R$ 10.000,00 desembolsados: 149910 + 1000000 = 1149910
        status_code, bal_data = get(f"/accounts/{pj_key}/balance")
        assert status_code == 200
        assert bal_data["balance"] == 1149910

        # Nova cobrança PIX liquidada: deve reter 10% para a caixinha de trava de crédito!
        status_code, charge_data2 = post(
            f"/accounts/{pj_key}/charges",
            payload={
                "method": "PIX",
                "amount": 200000,  # R$ 2.000,00
                "due_date": due_date,
            },
        )
        charge_key2 = charge_data2["charge_key"]
        wh_payload2 = {"event": "payment.settled", "charge_key": charge_key2, "amount": 200000}
        sig2 = hmac.new(
            self.WEBHOOK_SECRET.encode("utf-8"),
            json.dumps(wh_payload2, sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        status_code, wh_res2 = post(
            "/webhooks/payments",
            payload=wh_payload2,
            headers={"X-Signature-SHA256": sig2},
        )
        assert status_code == 200
        # 10% de R$ 2.000,00 = R$ 200,00 = 20000 centavos retidos
        assert wh_res2["retained_for_credit"] == 20000

        # =========================================================================
        # 6. Rendimento Automático de Fluxo de Caixa CDB 100% CDI (RFC 06)
        # =========================================================================
        status_code, yield_data = post(
            "/treasury/accrue-yield",
            payload={"account_key": pj_key, "cdi_daily_rate": 0.00045},
        )
        assert status_code == 200
        assert yield_data["accrual_event"]["gross_yield"] > 0
        assert yield_data["accrual_event"]["net_yield"] > 0

        # Posição de CDB
        status_code, pos = get(f"/accounts/{pj_key}/yield-position")
        assert status_code == 200
        assert pos["accumulated_yield"] > 0

        # =========================================================================
        # 7. Governança Patrimonial e Transferência PJ -> PF (RFC 07, RFC 02)
        # =========================================================================
        # Tentativa de transferir PJ -> PF sem a caixinha do DAS preenchida deve falhar (422)
        status_code, fail_data = post(
            "/transactions/transfers",
            payload={
                "source_account_key": pj_key,
                "destination_account_key": pf_key,
                "amount": 50000,  # R$ 500,00
                "description": "Distribuição de Lucros MEI",
            },
        )
        assert status_code == 422
        assert fail_data["code"] == "QIT002009"

        # Preenche a caixinha do DAS via endpoint de depósito na caixinha
        status_code, das_funded = post(
            f"/accounts/{pj_key}/pockets/{das_pocket['pocket_key']}/deposit",
            payload={"amount": 7500},
        )
        assert status_code == 200
        assert das_funded["current_balance"] == 7500

        # Agora a transferência PJ -> PF deve ser aprovada!
        status_code, transfer_data = post(
            "/transactions/transfers",
            payload={
                "source_account_key": pj_key,
                "destination_account_key": pf_key,
                "amount": 50000,  # R$ 500,00
                "description": "Distribuição de Lucros MEI Aprovada",
            },
        )
        assert status_code == 200
        assert transfer_data["status"] == "completed"

        # Saldo da conta PF deve ser exatamente R$ 500,00 (50000 centavos)
        status_code, pf_bal = get(f"/accounts/{pf_key}/balance")
        assert status_code == 200
        assert pf_bal["balance"] == 50000

        # =========================================================================
        # 8. Auditoria de Partidas Dobradas no Ledger (RFC 02, ADR-0004)
        # =========================================================================
        status_code, entries_pj = get(f"/accounts/{pj_key}/statement")
        assert status_code == 200
        assert len(entries_pj) >= 4

        status_code, entries_pf = get(f"/accounts/{pf_key}/statement")
        assert status_code == 200
        assert len(entries_pf) == 1
        assert entries_pf[0]["entry_type"] == "CREDIT"
        assert entries_pf[0]["amount"] == 50000
