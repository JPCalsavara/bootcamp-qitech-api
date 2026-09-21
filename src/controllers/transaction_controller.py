import hashlib
import json
from typing import List, Optional

from controllers.base_controller import BaseController
from dtos.transaction_dto import LedgerEntryDTO, TransactionDTO
from errors.custom_errors import InsufficientFunds, NotFoundAccount, PolicyViolation
from repositories.account_repository import AccountRepository
from repositories.ledger_repository import LedgerRepository
from repositories.pocket_repository import PocketRepository


class TransactionController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.ledger_repository = LedgerRepository(self.context)
        self.account_repository = AccountRepository(self.context)
        self.pocket_repository = PocketRepository(self.context)

    def execute_transfer(self, payload: dict, idempotency_key: Optional[str] = None) -> dict:
        src_key = payload["source_account_key"]
        dst_key = payload["destination_account_key"]
        amount = payload["amount"]
        description = payload.get("description", "Transferência entre contas")

        # 1. Idempotência (ADR-0006)
        if idempotency_key:
            cached = self.ledger_repository.get_idempotency(idempotency_key)
            if cached:
                return cached.response_body

        src_account = self.account_repository.get_by_key(src_key)
        if not src_account:
            raise NotFoundAccount(src_key)

        dst_account = self.account_repository.get_by_key(dst_key)
        if not dst_account:
            raise NotFoundAccount(dst_key)

        # 2. Verificação de Governança Patrimonial (RFC 07): PJ -> PF
        if src_account.account_type.enumerator == "PJ" and dst_account.account_type.enumerator == "PF":
            policy = self.pocket_repository.get_transfer_policy_by_pj(src_account.id)
            if policy:
                if amount > policy.max_daily_transfer_amount:
                    raise PolicyViolation(
                        f"Transferência excede o limite diário de R$ {policy.max_daily_transfer_amount / 100:.2f}"
                    )
                if policy.das_reserved_check:
                    # Verifica se o bolso DAS tem fundos
                    pockets = self.pocket_repository.get_pockets_by_account_id(src_account.id)
                    das_pocket = next((p for p in pockets if p.pocket_type.enumerator == "DAS_IMPOSTOS"), None)
                    if das_pocket and das_pocket.current_balance < das_pocket.target_amount:
                        raise PolicyViolation(
                            "Transferência PJ -> PF bloqueada: Caixinha de DAS-MEI não atingiu o valor reservado."
                        )

        # 3. Execução no Ledger com Trava Dijkstra e Partidas Dobradas
        try:
            tx = self.ledger_repository.execute_transfer(
                source_account=src_account,
                dest_account=dst_account,
                amount=amount,
                type_enum="TRANSFER_INTERNAL",
                description=description,
                idempotency_key=idempotency_key,
            )
        except Exception as e:
            if "INSUFFICIENT_FUNDS" in str(e):
                raise InsufficientFunds()
            raise e

        response_body = TransactionDTO.obj_to_dict(tx)

        # Salva idempotência se chave fornecida
        if idempotency_key:
            req_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
            self.ledger_repository.save_idempotency(
                idempotency_key=idempotency_key,
                request_hash=req_hash,
                response_code=200,
                response_body=response_body,
            )

        return response_body

    def execute_cash_in(self, payload: dict) -> dict:
        acc_key = payload["account_key"]
        amount = payload["amount"]
        fee_amount = payload.get("fee_amount", 0)
        description = payload.get("description", "Depósito em conta")

        account = self.account_repository.get_by_key(acc_key)
        if not account:
            raise NotFoundAccount(acc_key)

        tx = self.ledger_repository.execute_cash_in(
            dest_account=account,
            amount=amount,
            fee_amount=fee_amount,
            type_enum="PIX_CASH_IN",
            description=description,
        )
        return TransactionDTO.obj_to_dict(tx)

    def get_statement(self, account_key: str, limit: int = 50, offset: int = 0) -> List[dict]:
        account = self.account_repository.get_by_key(account_key)
        if not account:
            raise NotFoundAccount(account_key)

        entries = self.ledger_repository.get_entries_by_account_id(account.id, limit=limit, offset=offset)
        return [LedgerEntryDTO.obj_to_dict(entry) for entry in entries]
