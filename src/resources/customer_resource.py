from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import CustomerController
from utils.schema_handler import SchemaHandler


class CustomerResource:
    """Porta de entrada HTTP para Customer e Onboarding Seguro."""

    @SchemaHandler.validate("post_customer.json")
    def on_post(self, payload: dict) -> JSONResponse:
        controller = CustomerController()
        customer = controller.create(payload)

        return JSONResponse(
            content=jsonable_encoder(customer),
            status_code=http_status.HTTP_202_ACCEPTED,
        )

    def on_get_by_key(self, customer_key: str) -> JSONResponse:
        controller = CustomerController()
        customer = controller.get_by_key(customer_key)

        return JSONResponse(
            content=jsonable_encoder(customer),
            status_code=http_status.HTTP_200_OK,
        )
