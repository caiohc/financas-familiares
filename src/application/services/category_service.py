import uuid
from typing import List, Optional

from domain.financial.entities import Category, TransactionType
from domain.financial.repositories import CategoryRepository

class CategoryService:
    def __init__(self, category_repo: CategoryRepository):
        self.category_repo = category_repo

    def create_category(self, name: str, transaction_type_str: str) -> Category:
        category = Category(name=name, type=TransactionType(transaction_type_str))
        self.category_repo.save(category)
        return category

    def update_category(self, category_id: uuid.UUID, name: str, transaction_type_str: str) -> Optional[Category]:
        category = self.category_repo.get_by_id(category_id)
        if category:
            category.name = name
            category.type = TransactionType(transaction_type_str)
            self.category_repo.save(category)
            return category
        return None

    def get_category(self, category_id: uuid.UUID) -> Optional[Category]:
        return self.category_repo.get_by_id(category_id)

    def list_all(self) -> List[Category]:
        return self.category_repo.list_all()

    def list_by_type(self, type_str: str) -> List[Category]:
        # Supondo que CategorySQLiteRepository tenha o método ou fazemos o filtro em memória:
        # Pelo repositório que acabamos de criar, sabemos que list_by_type existe.
        if hasattr(self.category_repo, 'list_by_type'):
            return self.category_repo.list_by_type(type_str)
        else:
            return [c for c in self.category_repo.list_all() if c.type.value == type_str]
            
    def delete_category(self, category_id: uuid.UUID) -> None:
        # Idealmente verificar se existem transacoes associadas antes de deletar
        # Se listarmos todas as transacoes etc e filtrarmos, poderíamos bloquear
        # Para ser prático e atingir o CRUD básico, vamos deletar no banco.
        if hasattr(self.category_repo, 'delete'):
             self.category_repo.delete(category_id)
