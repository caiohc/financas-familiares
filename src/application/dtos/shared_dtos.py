from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

@dataclass(kw_only=True)
class DeletionPreviewDTO:
    """
    O que a tela de confirmação precisa saber antes de oferecer a exclusão:
    o nome do registro e, se houver dependências, o motivo do bloqueio.
    """
    name: str
    blocked_reason: Optional[str] = None


# Quantidades de registros por página que a pessoa pode escolher na listagem.
ALLOWED_PAGE_SIZES = (10, 25, 50)
DEFAULT_PAGE_SIZE = 10

# Ordenação das listagens: um campo por vez, em um dos dois sentidos.
DEFAULT_SORT_FIELD = "name"
SORT_DIRECTIONS = ("asc", "desc")

T = TypeVar("T")


@dataclass(kw_only=True)
class PageDTO(Generic[T]):
    """Uma página de listagem já normalizada pelo serviço (página e tamanho válidos)."""
    items: list[T]
    page: int
    page_size: int
    total: int
    sort_by: str = DEFAULT_SORT_FIELD
    sort_dir: str = "asc"
    search: str = ""

    @property
    def total_pages(self) -> int:
        return max(1, -(-self.total // self.page_size))

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages
