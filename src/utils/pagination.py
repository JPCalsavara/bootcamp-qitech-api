from typing import Mapping, Tuple

from errors.base_error import InvalidParameter


def parse_limit_offset(
    query_params: Mapping[str, str],
    default_limit: int = 50,
    max_limit: int = 200,
) -> Tuple[int, int]:
    """Lê e valida os parâmetros de paginação 'limit' e 'offset' da query string.

    Retorna a tupla (limit, offset). Levanta InvalidParameter (QIT000010, HTTP 400)
    quando os valores não são inteiros, quando offset é negativo ou quando limit
    está fora da faixa 1..max_limit.
    """
    raw_limit = query_params.get("limit")
    raw_offset = query_params.get("offset")

    limit = default_limit
    if raw_limit is not None:
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            raise InvalidParameter(f"O parâmetro 'limit' deve ser um inteiro, recebido: {raw_limit}.")
        if limit < 1 or limit > max_limit:
            raise InvalidParameter(f"O parâmetro 'limit' deve estar entre 1 e {max_limit}.")

    offset = 0
    if raw_offset is not None:
        try:
            offset = int(raw_offset)
        except (TypeError, ValueError):
            raise InvalidParameter(f"O parâmetro 'offset' deve ser um inteiro, recebido: {raw_offset}.")
        if offset < 0:
            raise InvalidParameter("O parâmetro 'offset' não pode ser negativo.")

    return limit, offset
