from abc import ABC, abstractmethod
from typing import Any
from domain.family.repositories import FamilyRepository, FamilyCostCenterRepository, MemberRepository
from domain.financial.repositories import CategoryRepository

class AbstractUnitOfWork(ABC):
    """
    Contrato da Unidade de Trabalho (Unit of Work).
    Garante que as operações no banco sejam atômicas.
    """
    families: FamilyRepository
    members: MemberRepository
    family_cost_centers: FamilyCostCenterRepository
    categories: CategoryRepository

    def __enter__(self) -> 'AbstractUnitOfWork':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.rollback()

    @abstractmethod
    def commit(self) -> None:
        """Confirma a transação pendente."""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Desfaz a transação pendente."""
        pass
