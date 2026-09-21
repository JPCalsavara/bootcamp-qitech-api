from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import KycController
from utils.schema_handler import SchemaHandler


class KycResource:
    @SchemaHandler.validate("post_kyc_analysis.json")
    def on_post_analysis(self, customer_key: str, payload: dict) -> JSONResponse:
        controller = KycController()
        result = controller.analyze(customer_key, payload)
        return JSONResponse(
            content=jsonable_encoder(result),
            status_code=http_status.HTTP_200_OK,
        )
