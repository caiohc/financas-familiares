import uuid
from typing import Optional

from domain.financial.entities import Category
from domain.financial.repositories import CategoryRepository
from domain.shared.pagination import Page
from domain.shared.text import fold_text


class FakeCategoryRepository(CategoryRepository):
    """
    Fake Repository centralizado para testes.
    Armazena os dados em memória RAM usando um dicionário.
    """
    def __init__(self):
        self.categories = {}
        self._has_deps = False

    def save(self, category: Category) -> None:
        self.categories[category.id] = category

    def get_by_id(self, category_id: uuid.UUID) -> Optional[Category]:
        return self.categories.get(category_id)

    def get_by_name(self, name: str) -> Optional[Category]:
        for category in self.categories.values():
            if category.name.lower() == name.lower():
                return category
        return None

    def list_all(self) -> list[Category]:
        return list(self.categories.values())

    def list_page(self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
                  search=None) -> Page:
        if sort_by not in ("name", "type"):
            raise ValueError(f"Campo de ordenação inválido: {sort_by!r}.")
        types = Category.types_matching(search) if search else []
        found = [
            c for c in self.categories.values()
            if not search or fold_text(search) in fold_text(c.name) or c.type in types
        ]
        ordered = sorted(found, key=lambda c: (c.name.lower(), str(c.id)))
        if sort_by == "type":
            ordered = sorted(ordered, key=lambda c: c.type.value.lower(), reverse=descending)
        else:
            ordered = sorted(ordered, key=lambda c: c.name.lower(), reverse=descending)
        start = (page - 1) * page_size
        return Page(items=ordered[start:start + page_size], total=len(ordered))

    def delete(self, category_id: uuid.UUID) -> None:
        if category_id in self.categories:
            del self.categories[category_id]

    def has_dependencies(self, category_id: uuid.UUID) -> bool:
        return self._has_deps

    def set_has_dependencies(self, value: bool):
        """Método auxiliar exclusivo para testes manipularem o estado do Fake."""
        self._has_deps = value
