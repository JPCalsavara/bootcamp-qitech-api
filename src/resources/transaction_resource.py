from fastapi import Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import TransactionController
from utils.pagination import parse_limit_offset
from utils.schema_handler import SchemaHandler


class TransactionResource:
    @SchemaHandler.validate("post_transfer.json")
    def on_post_transfer(self, payload: dict, request: Request) -> JSONResponse:
        idempotency_key = request.headers.get("Idempotency-Key") or request.headers.get("idempotency-key")
        controller = TransactionController()
        transaction = controller.execute_transfer(payload, idempotency_key=idempotency_key)
        return JSONResponse(
            content=jsonable_encoder(transaction),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate("post_cash_in.json")
    def on_post_cash_in(self, payload: dict) -> JSONResponse:
        controller = TransactionController()
        transaction = controller.execute_cash_in(payload)
        return JSONResponse(
            content=jsonable_encoder(transaction),
            status_code=http_status.HTTP_200_OK,
        )

    def on_get_statement(self, account_key: str, request: Request) -> JSONResponse:
        limit, offset = parse_limit_offset(request.query_params)
        controller = TransactionController()
        statement = controller.get_statement(account_key, limit=limit, offset=offset)
        return JSONResponse(
            content=jsonable_encoder(statement),
            status_code=http_status.HTTP_200_OK,
        )
