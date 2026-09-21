from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import AccountController


class AccountResource:
    def on_post_twin_accounts(self, customer_key: str) -> JSONResponse:
        controller = AccountController()
        accounts = controller.create_twin_accounts(customer_key)
        return JSONResponse(
            content=jsonable_encoder(accounts),
            status_code=http_status.HTTP_201_CREATED,
        )

    def on_get_by_key(self, account_key: str) -> JSONResponse:
        controller = AccountController()
        account = controller.get_by_key(account_key)
        return JSONResponse(
            content=jsonable_encoder(account),
            status_code=http_status.HTTP_200_OK,
        )

    def on_get_by_customer(self, customer_key: str) -> JSONResponse:
        controller = AccountController()
        accounts = controller.get_by_customer(customer_key)
        return JSONResponse(
            content=jsonable_encoder(accounts),
            status_code=http_status.HTTP_200_OK,
        )

    def on_get_balance(self, account_key: str) -> JSONResponse:
        controller = AccountController()
        balance_info = controller.get_balance(account_key)
        return JSONResponse(
            content=jsonable_encoder(balance_info),
            status_code=http_status.HTTP_200_OK,
        )

    def on_put_status(self, account_key: str, payload: dict) -> JSONResponse:
        controller = AccountController()
        result = controller.update_status(account_key, payload)
        return JSONResponse(
            content=jsonable_encoder(result),
            status_code=http_status.HTTP_202_ACCEPTED,
        )

    def on_put_blocked_balance(self, account_key: str, payload: dict) -> JSONResponse:
        controller = AccountController()
        result = controller.update_blocked_balance(account_key, payload)
        return JSONResponse(
            content=jsonable_encoder(result),
            status_code=http_status.HTTP_200_OK,
        )

