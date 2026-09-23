from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import CreditController
from utils.schema_handler import SchemaHandler


class CreditResource:
    @SchemaHandler.validate("post_credit_contract.json")
    def on_post_contract(self, payload: dict) -> JSONResponse:
        controller = CreditController()
        contract = controller.contract_credit(payload)
        return JSONResponse(
            content=jsonable_encoder(contract),
            status_code=http_status.HTTP_201_CREATED,
        )

    def on_get_contract(self, contract_key: str) -> JSONResponse:
        controller = CreditController()
        contract = controller.get_contract(contract_key)
        return JSONResponse(
            content=jsonable_encoder(contract),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate("post_anticipation.json")
    def on_post_anticipation(self, payload: dict) -> JSONResponse:
        controller = CreditController()
        anticipation = controller.anticipate_receivables(payload)
        return JSONResponse(
            content=jsonable_encoder(anticipation),
            status_code=http_status.HTTP_201_CREATED,
        )

    @SchemaHandler.validate("post_cross_guarantee.json")
    def on_post_cross_guarantee(self, payload: dict) -> JSONResponse:
        controller = CreditController()
        result = controller.execute_cross_guarantee(payload)
        return JSONResponse(
            content=jsonable_encoder(result),
            status_code=http_status.HTTP_200_OK,
        )

