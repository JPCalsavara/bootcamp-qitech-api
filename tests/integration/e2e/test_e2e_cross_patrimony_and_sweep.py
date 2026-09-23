from datetime import date, timedelta
import random
from tests.utils import ClientRequisition, RandomGenerator
from tests.utils.request_generator import INTERNAL_TOKEN


class TestE2ECrossPatrimonyAndSweep:
    """Jornada E2E 3: Resiliência Financeira, Cash Sweep Invisível de CDB e Garantia Cruzada PF/PJ.

    Cobre:
    - RFC 03: Governança de Caixa, Caixinhas e Cash Sweep Invisível no Débito (CDB 100% CDI)
    - RFC 04: Linhas de Crédito CCB, Trava de Recebíveis e Compensação Cruzada Art. 368 do Código Civil
    - ADR-0002: Locks de concorrência Dijkstra em transferências atômicas
    - ADR-0004: Partidas dobradas rastreáveis em livro-razão imutável
    """

    def _setup_customer_and_accounts(self) -> tuple[str, str, str]:
        cpf = RandomGenerator.generate_cpf()
        random_suffix = f"{random.randint(10000, 99999)}"
        email = f"resilience_{random_suffix}@exemplo.com.br"
        cnpj = f"12.345.678/{random.randint(1000, 9999)}-90"

        payload = {
            "name": "Carlos Empreendedor",
            "legal_name": "Carlos Consultoria e Servicos MEI LTDA",
            "email": email,
            "cpf": cpf,
            "cnpj": cnpj,
            "birthdate": "1988-03-22",
            "phone": "+5511966665555",
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
            payload={"score": 820, "risk_tier": "LOW", "flags": {"pep": False, "sanctions": False}},
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

    def _setup_supplier_account(self) -> str:
        cpf = RandomGenerator.generate_cpf()
        random_suffix = f"{random.randint(10000, 99999)}"
        payload = {
            "name": "Fornecedor Materiais",
            "legal_name": "Fornecedor Materiais LTDA",
            "email": f"fornecedor_{random_suffix}@exemplo.com.br",
            "cpf": cpf,
            "cnpj": f"98.765.432/{random.randint(1000, 9999)}-10",
            "birthdate": "1985-01-10",
            "phone": "+5511955553333",
            "password": "SenhaForte@2026",
            "transaction_pin": "1234",
        }
        resp = ClientRequisition.send("POST", "/customers", payload=payload, headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        cust_key = resp.response_json["customer_key"]
        resp_acc = ClientRequisition.send("POST", f"/customers/{cust_key}/accounts", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        pj = next(a for a in resp_acc.response_json if a["type"] == "PJ")
        return pj["account_key"]

    def test_e2e_journey_resilience_cash_sweep_and_cross_guarantee(self) -> None:
        customer_key, pj_key, pf_key = self._setup_customer_and_accounts()
        supplier_key = self._setup_supplier_account()

        # =========================================================================
        # FASE 1: Gestão de Tesouraria & Investimento em CDB Remunerado (RFC 03)
        # =========================================================================
        # Aporte inicial na PJ: R$ 10.000,00 (1.000.000 centavos)
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": pj_key, "amount": 1000000, "description": "Capital de Giro Inicial"},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        # Investe R$ 8.000,00 em CDB com liquidez diária
        resp_invest = ClientRequisition.send(
            "POST",
            "/treasury/invest",
            payload={"account_key": pj_key, "amount": 800000},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_invest.response_status == 200
        assert resp_invest.response_json["principal_amount"] == 800000

        # Saldo livre agora é R$ 2.000,00 (200.000 centavos)
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 200000

        # Reserva pessoal do empreendedor na conta PF: R$ 4.000,00 (400.000 centavos)
        ClientRequisition.send(
            "POST",
            "/transactions/cash-in",
            payload={"account_key": pf_key, "amount": 400000, "description": "Reserva Pessoal PF"},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        # =========================================================================
        # FASE 2: Contratação de Crédito CCB com Trava de Recebíveis (RFC 04)
        # =========================================================================
        resp_credit = ClientRequisition.send(
            "POST",
            "/credit/contracts",
            payload={
                "customer_key": customer_key,
                "account_pj_key": pj_key,
                "account_pf_key": pf_key,
                "requested_amount": 600000,  # R$ 6.000,00
                "term_months": 6,
                "interest_rate_monthly": 0.02,
                "retention_percentage": 10.0,
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_credit.response_status == 201
        contract = resp_credit.response_json
        contract_key = contract["contract_key"]
        inst_1 = contract["installments"][0]
        inst_amount = inst_1["amount"]

        # Saldo livre na PJ agora: 200.000 + 600.000 = 800.000 centavos (R$ 8.000,00)
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 800000

        # =========================================================================
        # FASE 3: Estresse de Caixa & Resgate Automático Invisível (Cash Sweep)
        # =========================================================================
        # Pagamento de duplicata do fornecedor de R$ 10.000,00 (1.000.000 centavos).
        # Saldo livre é R$ 8.000,00. Déficit de R$ 2.000,00 (200.000 centavos).
        # O Cash Sweep deve resgatar R$ 2.000,00 do CDB (que tem R$ 8.000,00) e liquidar os R$ 10.000,00!
        resp_sweep_tx = ClientRequisition.send(
            "POST",
            "/transactions/transfers",
            payload={
                "source_account_key": pj_key,
                "destination_account_key": supplier_key,
                "amount": 1000000,
                "description": "Pagamento de Maquinário com Cash Sweep",
            },
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_sweep_tx.response_status == 200

        # Saldo livre na PJ após o pagamento: 800.000 + 200.000 (resgate) - 1.000.000 = 0
        resp_bal = ClientRequisition.send("GET", f"/accounts/{pj_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_bal.response_json["balance"] == 0

        # Posição de CDB após o resgate: 800.000 - 200.000 = 600.000 centavos (R$ 6.000,00)
        resp_pos = ClientRequisition.send("GET", f"/accounts/{pj_key}/yield-position", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_pos.response_json["principal_amount"] == 600000

        # Fornecedor recebeu o valor integral
        resp_supp_bal = ClientRequisition.send("GET", f"/accounts/{supplier_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_supp_bal.response_json["balance"] == 1000000

        # Extrato PJ audita as partidas: crédito de Cash Sweep e débito de transferência
        resp_stmt = ClientRequisition.send("GET", f"/accounts/{pj_key}/statement", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        entries = resp_stmt.response_json
        assert any(e["entry_type"] == "CREDIT" and e["amount"] == 200000 and "Cash Sweep" in e["description"] for e in entries)
        assert any(e["entry_type"] == "DEBIT" and e["amount"] == 1000000 for e in entries)

        # =========================================================================
        # FASE 4: Estresse de Inadimplência & Garantia Cruzada PF/PJ (RFC 04)
        # =========================================================================
        # Parcela 1 da CCB vence em today + 30 dias.
        # A empresa teve faturamento zerado no mês.
        # 1. Execução do job dentro da janela de tolerância de 5 dias (atraso de 3 dias):
        target_date_grace = (date.today() + timedelta(days=33)).isoformat()
        resp_grace = ClientRequisition.send(
            "POST",
            "/credit/cross-guarantee/execute",
            payload={"contract_key": contract_key, "target_date": target_date_grace},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_grace.response_status == 200
        assert resp_grace.response_json["settled_installments"] == 0
        # Conta PF não é tocada durante a carência
        resp_pf_bal = ClientRequisition.send("GET", f"/accounts/{pf_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_pf_bal.response_json["balance"] == 400000

        # 2. Execução do job após estourar a carência (atraso de 10 dias):
        target_date_overdue = (date.today() + timedelta(days=40)).isoformat()
        resp_cross = ClientRequisition.send(
            "POST",
            "/credit/cross-guarantee/execute",
            payload={"contract_key": contract_key, "target_date": target_date_overdue},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert resp_cross.response_status == 200
        assert resp_cross.response_json["settled_installments"] == 1
        assert resp_cross.response_json["total_settled_amount"] == inst_amount

        # Parcela 1 agora está totalmente PAGA
        resp_contract = ClientRequisition.send("GET", f"/credit/contracts/{contract_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_contract.response_json["installments"][0]["status"] == "PAID"
        assert resp_contract.response_json["installments"][0]["paid_amount"] == inst_amount

        # Conta PF do titular arcou com a obrigação (Art. 368 CC)
        resp_pf_bal2 = ClientRequisition.send("GET", f"/accounts/{pf_key}/balance", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert resp_pf_bal2.response_json["balance"] == 400000 - inst_amount

        # Extrato PF registra a liquidação de garantia cruzada
        resp_pf_stmt = ClientRequisition.send("GET", f"/accounts/{pf_key}/statement", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert any(e["entry_type"] == "DEBIT" and e["amount"] == inst_amount and "Garantia Cruzada" in e["description"] for e in resp_pf_stmt.response_json)
