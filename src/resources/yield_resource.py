from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import YieldController
from utils.schema_handler import SchemaHandler


class YieldResource:
    @SchemaHandler.validate("post_accrue_yield.json")
    def on_post_accrue(self, payload: dict) -> JSONResponse:
        controller = YieldController()
        result = controller.accrue_yield(payload)
        return JSONResponse(
            content=jsonable_encoder(result),
            status_code=http_status.HTTP_200_OK,
        )

    def on_get_position(self, account_key: str) -> JSONResponse:
        controller = YieldController()
        pos = controller.get_position(account_key)
        return JSONResponse(
            content=jsonable_encoder(pos),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate("post_invest_treasury.json")
    def on_post_invest(self, payload: dict) -> JSONResponse:
        controller = YieldController()
        result = controller.invest(payload)
        return JSONResponse(
            content=jsonable_encoder(result),
            status_code=http_status.HTTP_200_OK,
        )

