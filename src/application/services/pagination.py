from typing import Callable, Optional, Sequence, TypeVar

from application.dtos.shared_dtos import (
    ALLOWED_PAGE_SIZES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT_FIELD,
    SORT_DIRECTIONS,
    PageDTO,
)
from domain.shared.pagination import Page

MAX_SEARCH_LENGTH = 100

T = TypeVar("T")
R = TypeVar("R")


def build_page(
    fetch: Callable[[int, int, str, bool, Optional[str]], Page[T]],
    to_dto: Callable[[T], R],
    page: Optional[int],
    page_size: Optional[int],
    sort_by: Optional[str],
    sort_dir: Optional[str],
    sortable_fields: Sequence[str],
    search: Optional[str] = None,
) -> PageDTO[R]:
    """
    Regras de paginação e ordenação comuns às listagens: tamanho fora da lista
    permitida volta ao padrão, página inválida vira a primeira e página além
    da última devolve a última (ex.: a pessoa excluiu o único registro da
    última página). Ordena por um único campo da lista permitida (senão, pelo
    nome) e, se o sentido não for "asc" ou "desc", em ordem ascendente. A pesquisa
    (sem espaços nas pontas, até MAX_SEARCH_LENGTH caracteres) restringe a lista; a página
    e o total passam a valer sobre o resultado.
    """
    size = page_size if page_size in ALLOWED_PAGE_SIZES else DEFAULT_PAGE_SIZE
    number = page if isinstance(page, int) and page >= 1 else 1
    field = sort_by if sort_by in sortable_fields else DEFAULT_SORT_FIELD
    direction = sort_dir if sort_dir in SORT_DIRECTIONS else "asc"
    descending = direction == "desc"
    term = (search or "").strip()[:MAX_SEARCH_LENGTH]

    result = fetch(number, size, field, descending, term or None)
    last_page = max(1, -(-result.total // size))
    if number > last_page:
        number = last_page
        result = fetch(number, size, field, descending, term or None)

    return PageDTO(
        items=[to_dto(i) for i in result.items], page=number, page_size=size, total=result.total,
        sort_by=field, sort_dir=direction, search=term,
    )
