from fastapi import FastAPI

from constants import check_variables
from errors import register_error_handlers
from errors.base_error import error_verification
from middlewares import (
    register_internal_token_middleware,
    register_request_context_middleware,
    register_request_logger_middleware,
    register_session_manager_middleware,
)
from resources import (
    AccountResource,
    ChargeResource,
    CreditResource,
    CustomerResource,
    HealthCheckResource,
    KycResource,
    PocketResource,
    SampleEntityResource,
    TransactionResource,
    YieldResource,
)
from utils.logger import setup_logging


def create_app() -> FastAPI:
    application = FastAPI(
        title="Bootcamp QI Tech - MEI Financial Platform",
        description="API bancária completa para o MEI: Onboarding seguro, contas gêmeas PF/PJ, ledger de partidas dobradas, liquidação bruta com tarifa atômica, crédito com trava de recebíveis, CDB 100% CDI e governança de caixinhas.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )


    register_session_manager_middleware(application)
    register_internal_token_middleware(application)
    register_request_logger_middleware(application)
    register_request_context_middleware(application)

    health_check_resource = HealthCheckResource()
    sample_entity_resource = SampleEntityResource()
    customer_resource = CustomerResource()
    account_resource = AccountResource()
    transaction_resource = TransactionResource()
    kyc_resource = KycResource()
    charge_resource = ChargeResource()
    credit_resource = CreditResource()
    yield_resource = YieldResource()
    pocket_resource = PocketResource()

    # Health check
    application.add_api_route("/", health_check_resource.on_get_home, methods=["GET"])
    application.add_api_route("/health_check", health_check_resource.on_get_health_check, methods=["GET"])

    # Sample Entity
    application.add_api_route("/sample_entity", sample_entity_resource.on_post, methods=["POST"])
    application.add_api_route("/sample_entity/{sample_entity_key}", sample_entity_resource.on_get_by_key, methods=["GET"])
    application.add_api_route("/sample_entity/{sample_entity_key}", sample_entity_resource.on_put_by_key, methods=["PUT"])
    application.add_api_route("/webhook/sample_entity/{sample_entity_key}/increment_counter", sample_entity_resource.on_put_increment_counter, methods=["PUT"])
    application.add_api_route("/sample_entities", sample_entity_resource.on_get_list, methods=["GET"])

    # RFC 01 & RFC 03: Customer & Onboarding
    application.add_api_route("/customers", customer_resource.on_post, methods=["POST"])
    application.add_api_route("/customers/{customer_key}", customer_resource.on_get_by_key, methods=["GET"])
    application.add_api_route("/customers/{customer_key}/kyc/analysis", kyc_resource.on_post_analysis, methods=["POST"])

    # RFC 01: Twin Accounts (PF & PJ) & Account Lifecycle
    application.add_api_route("/customers/{customer_key}/accounts", account_resource.on_post_twin_accounts, methods=["POST"])
    application.add_api_route("/customers/{customer_key}/accounts", account_resource.on_get_by_customer, methods=["GET"])
    application.add_api_route("/accounts/{account_key}", account_resource.on_get_by_key, methods=["GET"])
    application.add_api_route("/accounts/{account_key}/balance", account_resource.on_get_balance, methods=["GET"])
    application.add_api_route("/accounts/{account_key}/status", account_resource.on_put_status, methods=["PUT"])
    application.add_api_route("/accounts/{account_key}/blocked-balance", account_resource.on_put_blocked_balance, methods=["PUT"])

    # RFC 02: Ledger, Transfers, Cash-in & Statements
    application.add_api_route("/transactions/transfers", transaction_resource.on_post_transfer, methods=["POST"])
    application.add_api_route("/transactions/cash-in", transaction_resource.on_post_cash_in, methods=["POST"])
    application.add_api_route("/accounts/{account_key}/statement", transaction_resource.on_get_statement, methods=["GET"])

    # RFC 04: Meios de Pagamento & Webhook HMAC
    application.add_api_route("/accounts/{account_key}/charges", charge_resource.on_post_charge, methods=["POST"])
    application.add_api_route("/charges/{charge_key}", charge_resource.on_get_charge, methods=["GET"])
    application.add_api_route("/charges/reconciliation", charge_resource.on_post_reconciliation, methods=["POST"])
    application.add_api_route("/webhooks/payments", charge_resource.on_post_webhook, methods=["POST"])

    # RFC 05: Linhas de Crédito & Trava de Recebíveis
    application.add_api_route("/credit/contracts", credit_resource.on_post_contract, methods=["POST"])
    application.add_api_route("/credit/contracts/{contract_key}", credit_resource.on_get_contract, methods=["GET"])
    application.add_api_route("/credit/anticipations", credit_resource.on_post_anticipation, methods=["POST"])
    application.add_api_route("/credit/cross-guarantee/execute", credit_resource.on_post_cross_guarantee, methods=["POST"])

    # RFC 06: Tesouraria & Fluxo Remunerado (CDB 100% CDI)
    application.add_api_route("/treasury/accrue-yield", yield_resource.on_post_accrue, methods=["POST"])
    application.add_api_route("/treasury/invest", yield_resource.on_post_invest, methods=["POST"])
    application.add_api_route("/accounts/{account_key}/yield-position", yield_resource.on_get_position, methods=["GET"])

    # RFC 07: Governança Patrimonial & Pockets (Caixinhas)
    application.add_api_route("/accounts/{account_key}/pockets", pocket_resource.on_post_pocket, methods=["POST"])
    application.add_api_route("/accounts/{account_key}/pockets", pocket_resource.on_get_pockets, methods=["GET"])
    application.add_api_route("/accounts/{account_key}/pockets/{pocket_key}/deposit", pocket_resource.on_post_deposit, methods=["POST"])
    application.add_api_route("/governance/transfer-policies", pocket_resource.on_post_transfer_policy, methods=["POST"])
    application.add_api_route("/customers/{customer_key}/revenue-tracker", pocket_resource.on_get_revenue_tracker, methods=["GET"])

    register_error_handlers(application)

    return application


def main() -> FastAPI:
    check_variables()
    error_verification()
    setup_logging()

    return create_app()


app = main()
