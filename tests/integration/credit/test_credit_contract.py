from datetime import date, timedelta
import hashlib
import hmac
import json
import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils import INTERNAL_TOKEN


class TestCreditContract:
    """RFC 05: Linhas de Crédito & Trava de Recebíveis."""

    WEBHOOK_SECRET = "qitech_bootcamp_secret_2026"

    def _setup_customer_and_accounts(self):
        cpf = RandomGenerator.generate_cpf()
        random_digits = f"{random.randint(1000, 9999)}"
        email = f"credit.{random_digits}@exemplo.com.br"
        cnpj = RandomGenerator.generate_cnpj()

        payload = {
            "name": "Cliente Credito",
            "legal_name": "Cliente Credito MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1989-11-25",
            "phone": "+5511955554444",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }

        resp = ClientRequisition.send("POST", "/customers", payload=payload, headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        customer_key = resp.response_json["customer_key"]

        resp_accounts = ClientRequisition.send(
            "POST",
            f"/customers/{customer_key}/accounts",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        accounts = resp_accounts.response_json
        pj_acc = next(a for a in accounts if a["type"] == "PJ")
        pf_acc = next(a for a in accounts if a["type"] == "PF")
        return customer_key, pj_acc["account_key"], pf_acc["account_key"]

    def test_credit_contract_creation_disbursement_and_installments(self) -> None:
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()

        contract_payload = {
            "customer_key": customer_key,
            "account_pj_key": pj_key,
            "account_pf_key": pf_key,
            "requested_amount": 500000,  # R$ 5.000,00
            "term_months": 6,
            "interest_rate_monthly": 0.02,
            "retention_percentage": 15.0,  # 15% de trava
        }

        resp_contract = ClientRequisition.send(
            "POST",
            "/credit/contracts",
            payload=contract_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_contract.response_status == 201
        contract = resp_contract.response_json
        assert contract["status"] == "disbursed"
        assert contract["requested_amount"] == 500000
        assert len(contract["installments"]) == 6
        assert contract["pocket_key"] is not None

        contract_key = contract["contract_key"]

        # Verifica saldo na conta PJ: R$ 5.000,00 desembolsados
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 500000

        # Consulta contrato via GET /credit/contracts/{contract_key}
        resp_get = ClientRequisition.send(
            "GET",
            f"/credit/contracts/{contract_key}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_get.response_status == 200
        assert resp_get.response_json["contract_key"] == contract_key
        assert len(resp_get.response_json["installments"]) == 6

    def test_receivables_anticipation(self) -> None:
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()

        anticipation_payload = {
            "account_key": pj_key,
            "charge_keys": ["charge-key-1", "charge-key-2"],
            "discount_rate": 0.05,  # 5% de taxa de desconto
        }

        resp = ClientRequisition.send(
            "POST",
            "/credit/anticipations",
            payload=anticipation_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp.response_status == 201
        data = resp.response_json
        assert data["status"] == "COMPLETED"
        assert data["discount_fee"] > 0
        assert data["net_disbursed_amount"] == data["original_amount"] - data["discount_fee"]

        # Verifica se o valor líquido foi creditado na conta
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == data["net_disbursed_amount"]

    def test_receivables_retention_smart_cap_and_settle_due_installment(self) -> None:
        """Valida teto inteligente da trava de recebíveis e liquidação de parcelas via pocket."""
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()

        # 1. Contrato CCB de R$ 1.000,00 (100.000 centavos) em 2 parcelas com trava de 50%
        contract_payload = {
            "customer_key": customer_key,
            "account_pj_key": pj_key,
            "account_pf_key": pf_key,
            "requested_amount": 100000,
            "term_months": 2,
            "interest_rate_monthly": 0.02,
            "retention_percentage": 50.0,
        }
        resp_contract = ClientRequisition.send(
            "POST",
            "/credit/contracts",
            payload=contract_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_contract.response_status == 201
        contract_data = resp_contract.response_json
        contract_key = contract_data["contract_key"]
        pocket_key = contract_data["pocket_key"]
        inst_1 = contract_data["installments"][0]
        inst_1_amount = inst_1["amount"]

        # 2. Primeira cobrança PIX: R$ 1.500,00 (150.000 centavos)
        # 50% de R$ 1.500,00 seriam 75.000 centavos, que excedem o valor da parcela (~51.505).
        # O teto inteligente deve reter estritamente o déficit da parcela 1 (inst_1_amount)!
        resp_charge1 = ClientRequisition.send(
            "POST",
            f"/accounts/{pj_key}/charges",
            payload={"method": "PIX", "amount": 150000, "due_date": (date.today() + timedelta(days=5)).isoformat()},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_charge1.response_status == 201
        charge_key1 = resp_charge1.response_json["charge_key"]

        wh_payload1 = {"event": "payment.settled", "charge_key": charge_key1, "amount": 150000}
        sig1 = hmac.new(
            self.WEBHOOK_SECRET.encode("utf-8"),
            json.dumps(wh_payload1, sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        resp_wh1 = ClientRequisition.send(
            "POST",
            "/webhooks/payments",
            payload=wh_payload1,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "X-Signature-SHA256": sig1},
        )
        assert resp_wh1.response_status == 200
        assert resp_wh1.response_json["retained_for_credit"] == inst_1_amount

        # Verifica caixinha de amortização: saldo exatamente igual ao valor da parcela
        resp_pockets = ClientRequisition.send("GET", f"/accounts/{pj_key}/pockets", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        pocket = next(p for p in resp_pockets.response_json if p["pocket_key"] == pocket_key)
        assert pocket["current_balance"] == inst_1_amount

        # 3. Segunda cobrança PIX: R$ 500,00 (50.000 centavos)
        # Com a caixinha da parcela 1 já atingida (déficit == 0), a retenção deve ser 0!
        resp_charge2 = ClientRequisition.send(
            "POST",
            f"/accounts/{pj_key}/charges",
            payload={"method": "PIX", "amount": 50000, "due_date": (date.today() + timedelta(days=5)).isoformat()},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_charge2.response_status == 201
        charge_key2 = resp_charge2.response_json["charge_key"]

        wh_payload2 = {"event": "payment.settled", "charge_key": charge_key2, "amount": 50000}
        sig2 = hmac.new(
            self.WEBHOOK_SECRET.encode("utf-8"),
            json.dumps(wh_payload2, sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        resp_wh2 = ClientRequisition.send(
            "POST",
            "/webhooks/payments",
            payload=wh_payload2,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "X-Signature-SHA256": sig2},
        )
        assert resp_wh2.response_status == 200
        assert resp_wh2.response_json["retained_for_credit"] == 0

        # Saldo do pocket permanece inst_1_amount (não reteve nada a mais)
        resp_pockets_after = ClientRequisition.send("GET", f"/accounts/{pj_key}/pockets", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        pocket_after = next(p for p in resp_pockets_after.response_json if p["pocket_key"] == pocket_key)
        assert pocket_after["current_balance"] == inst_1_amount

        # 4. Quitação automática de parcelas vencidas via endpoint POST /credit/installments/settle-due
        resp_settle = ClientRequisition.send(
            "POST",
            "/credit/installments/settle-due",
            payload={"target_date": inst_1["due_date"]},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_settle.response_status == 200
        settle_data = resp_settle.response_json
        assert settle_data["settled_count"] >= 1
        assert any(d["contract_key"] == contract_key and d["status"] == "PAID_FROM_POCKET" for d in settle_data["details"])

        # Verifica contrato atualizado: parcela 1 agora está PAID
        resp_contract_after = ClientRequisition.send("GET", f"/credit/contracts/{contract_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_contract_after.response_json["installments"][0]["status"] == "PAID"

        # Verifica saldo do pocket debitado para 0
        resp_pockets_final = ClientRequisition.send("GET", f"/accounts/{pj_key}/pockets", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        pocket_final = next(p for p in resp_pockets_final.response_json if p["pocket_key"] == pocket_key)
        assert pocket_final["current_balance"] == 0
