import uuid
from typing import Optional

from domain.financial.entities import Category
from domain.financial.repositories import CategoryRepository


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

    def delete(self, category_id: uuid.UUID) -> None:
        if category_id in self.categories:
            del self.categories[category_id]

    def has_dependencies(self, category_id: uuid.UUID) -> bool:
        return self._has_deps

    def set_has_dependencies(self, value: bool):
        """Método auxiliar exclusivo para testes manipularem o estado do Fake."""
        self._has_deps = value
