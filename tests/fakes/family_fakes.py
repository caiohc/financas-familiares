import uuid
from typing import Optional
from domain.family.repositories import FamilyRepository
from domain.family.entities import Family

class FakeFamilyRepository(FamilyRepository):
    """
    Fake Repository centralizado para testes.
    Armazena os dados em memória RAM usando um dicionário.
    """
    def __init__(self):
        self.families = {}
        self._has_deps = False

    def save(self, family: Family) -> None:
        self.families[family.id] = family

    def get_by_id(self, family_id: uuid.UUID) -> Optional[Family]:
        return self.families.get(family_id)

    def list_all(self) -> list[Family]:
        return list(self.families.values())

    def delete(self, family_id: uuid.UUID) -> None:
        if family_id in self.families:
            del self.families[family_id]

    def has_dependencies(self, family_id: uuid.UUID) -> bool:
        return self._has_deps
        
    def set_has_dependencies(self, value: bool):
        """Método auxiliar exclusivo para testes manipularem o estado do Fake."""
        self._has_deps = value

from application.interfaces.unit_of_work import AbstractUnitOfWork

class FakeUnitOfWork(AbstractUnitOfWork):
    """
    Fake UnitOfWork para testes.
    Apenas gerencia o FakeRepository em RAM e registra chamadas de commit.
    """
    def __init__(self):
        self.families = FakeFamilyRepository()
        self.committed = False

    def __enter__(self):
        return super().__enter__()

    def commit(self):
        self.committed = True

    def rollback(self):
        pass
