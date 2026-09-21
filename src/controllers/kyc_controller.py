from connectors.kyc_connector import KycConnector
from controllers.base_controller import BaseController
from errors.custom_errors import NotFoundCustomer
from repositories.customer_repository import CustomerRepository
from repositories.kyc_repository import KycRepository


class KycController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.kyc_repository = KycRepository(self.context)
        self.customer_repository = CustomerRepository(self.context)
        self.kyc_connector = KycConnector()

    def analyze(self, customer_key: str, payload: dict) -> dict:
        customer = self.customer_repository.get_by_key(customer_key)
        if not customer:
            raise NotFoundCustomer(customer_key)

        score = payload.get("score")
        risk_tier = payload.get("risk_tier")
        cnd_federal = payload.get("cnd_federal_status")
        cnd_trabalhista = payload.get("cnd_trabalhista_status")
        cadsan = payload.get("cadsan_status")
        flags = payload.get("flags")
        recommendation = None

        # Se dados não foram passados diretamente no payload, consulta o KycConnector (serviço terceiro HTTP egress)
        if score is None:
            connector_data = self.kyc_connector.analyze_document(customer.cpf, customer.cnpj)
            score = connector_data["score"]
            risk_tier = risk_tier or connector_data.get("risk_tier", "LOW")
            cnd_federal = cnd_federal or connector_data.get("cnd_federal_status", "REGULAR")
            cnd_trabalhista = cnd_trabalhista or connector_data.get("cnd_trabalhista_status", "REGULAR")
            cadsan = cadsan or connector_data.get("cadsan_status", "REGULAR")
            flags = flags or connector_data.get("flags", {})
            recommendation = connector_data.get("recommendation")
        else:
            risk_tier = risk_tier or "LOW"
            cnd_federal = cnd_federal or "REGULAR"
            cnd_trabalhista = cnd_trabalhista or "REGULAR"
            cadsan = cadsan or "REGULAR"
            flags = flags or {}

        # Recomendação automática baseada no score e CNDs se não vier definida
        if not recommendation:
            if score >= 600 and cnd_federal == "REGULAR":
                recommendation = "APPROVE"
                to_status = "active"
                reason = "KYC_APPROVED_SCORE"
            elif score < 300:
                recommendation = "REJECT"
                to_status = "rejected"
                reason = "KYC_REJECTED_HIGH_RISK"
            else:
                recommendation = "MANUAL_REVIEW"
                to_status = "under_review"
                reason = "KYC_MANUAL_REVIEW_REQUIRED"
        else:
            if recommendation == "APPROVE":
                to_status = "active"
                reason = "KYC_APPROVED_EXTERNAL_SCORE"
            elif recommendation == "REJECT":
                to_status = "rejected"
                reason = "KYC_REJECTED_EXTERNAL_BUREAU"
            else:
                recommendation = "MANUAL_REVIEW"
                to_status = "under_review"
                reason = "KYC_MANUAL_REVIEW_REQUIRED"

        analysis = self.kyc_repository.create_analysis(
            customer_id=customer.id,
            risk_tier_enum=risk_tier,
            score=score,
            cnd_federal_status=cnd_federal,
            cnd_trabalhista_status=cnd_trabalhista,
            cadsan_status=cadsan,
            flags=flags,
            recommendation=recommendation,
        )

        customer = self.kyc_repository.transition_customer_status(
            customer_id=customer.id,
            to_status_enum=to_status,
            reason_code=reason,
            reason_detail={"score": score, "recommendation": recommendation},
        )

        return {
            "analysis_key": analysis.analysis_key,
            "customer_key": customer.customer_key,
            "customer_status": customer.status.enumerator,
            "score": score,
            "recommendation": recommendation,
            "risk_tier": risk_tier,
        }
