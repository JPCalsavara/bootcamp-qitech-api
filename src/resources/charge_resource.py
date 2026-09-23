from fastapi import Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import ChargeController
from utils.schema_handler import SchemaHandler


class ChargeResource:
    @SchemaHandler.validate("post_charge.json")
    def on_post_charge(self, account_key: str, payload: dict) -> JSONResponse:
        controller = ChargeController()
        charge = controller.create_charge(account_key, payload)
        return JSONResponse(
            content=jsonable_encoder(charge),
            status_code=http_status.HTTP_201_CREATED,
        )

    def on_get_charge(self, charge_key: str) -> JSONResponse:
        controller = ChargeController()
        charge = controller.get_charge(charge_key)
        return JSONResponse(
            content=jsonable_encoder(charge),
            status_code=http_status.HTTP_200_OK,
        )

    def on_post_webhook(self, payload: dict, request: Request) -> JSONResponse:
        signature = request.headers.get("X-Signature-SHA256") or request.headers.get("x-signature")
        timestamp = request.headers.get("X-Webhook-Timestamp") or request.headers.get("x-webhook-timestamp")
        nonce = request.headers.get("X-Webhook-Nonce") or request.headers.get("x-webhook-nonce")
        controller = ChargeController()
        result = controller.process_webhook(
            payload,
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
        )
        return JSONResponse(
            content=jsonable_encoder(result),
            status_code=http_status.HTTP_200_OK,
        )

    def on_post_reconciliation(self, payload: dict = None) -> JSONResponse:
        controller = ChargeController()
        result = controller.reconcile_charges(payload or {})
        return JSONResponse(
            content=jsonable_encoder(result),
            status_code=http_status.HTTP_200_OK,
        )

