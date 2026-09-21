from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import PocketController
from utils.schema_handler import SchemaHandler


class PocketResource:
    @SchemaHandler.validate("post_pocket.json")
    def on_post_pocket(self, account_key: str, payload: dict) -> JSONResponse:
        controller = PocketController()
        pocket = controller.create_pocket(account_key, payload)
        return JSONResponse(
            content=jsonable_encoder(pocket),
            status_code=http_status.HTTP_201_CREATED,
        )

    def on_get_pockets(self, account_key: str) -> JSONResponse:
        controller = PocketController()
        pockets = controller.get_pockets(account_key)
        return JSONResponse(
            content=jsonable_encoder(pockets),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate("post_transfer_policy.json")
    def on_post_transfer_policy(self, payload: dict) -> JSONResponse:
        controller = PocketController()
        policy = controller.create_transfer_policy(payload)
        return JSONResponse(
            content=jsonable_encoder(policy),
            status_code=http_status.HTTP_201_CREATED,
        )

    def on_get_revenue_tracker(self, customer_key: str) -> JSONResponse:
        controller = PocketController()
        tracker = controller.get_revenue_tracker(customer_key)
        return JSONResponse(
            content=jsonable_encoder(tracker),
            status_code=http_status.HTTP_200_OK,
        )

    def on_post_deposit(self, account_key: str, pocket_key: str, payload: dict) -> JSONResponse:
        controller = PocketController()
        pocket = controller.deposit_to_pocket(account_key, pocket_key, payload)
        return JSONResponse(
            content=jsonable_encoder(pocket),
            status_code=http_status.HTTP_200_OK,
        )

