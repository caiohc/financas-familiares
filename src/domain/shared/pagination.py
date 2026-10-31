from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    """Uma fatia de uma listagem ordenada, com o total de registros da listagem inteira."""
    items: list[T]
    total: int
