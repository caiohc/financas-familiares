import uuid
from typing import Optional
from domain.family.repositories import FamilyRepository, FamilyCostCenterRepository
from domain.family.entities import Family, FamilyCostCenter
from application.interfaces.unit_of_work import AbstractUnitOfWork


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

    def get_by_name(self, name: str) -> Optional[Family]:
        for family in self.families.values():
            if family.name.lower() == name.lower():
                return family
        return None

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


class FakeFamilyCostCenterRepository(FamilyCostCenterRepository):
    """
    Fake Repository centralizado para testes.
    Armazena os dados em memória RAM usando um dicionário.
    """
    def __init__(self):
        self.cost_centers = {}

    def save(self, cost_center: FamilyCostCenter) -> None:
        self.cost_centers[cost_center.id] = cost_center

    def get_by_id(self, cost_center_id: uuid.UUID) -> Optional[FamilyCostCenter]:
        return self.cost_centers.get(cost_center_id)

    def get_by_name(self, family_id: uuid.UUID, name: str) -> Optional[FamilyCostCenter]:
        for cost_center in self.cost_centers.values():
            if cost_center.family_id == family_id and cost_center.name.lower() == name.lower():
                return cost_center
        return None

    def list_by_family(self, family_id: uuid.UUID) -> list[FamilyCostCenter]:
        return [cc for cc in self.cost_centers.values() if cc.family_id == family_id]

    def delete(self, cost_center_id: uuid.UUID) -> None:
        if cost_center_id in self.cost_centers:
            del self.cost_centers[cost_center_id]


class FakeUnitOfWork(AbstractUnitOfWork):
    """
    Fake UnitOfWork para testes.
    Apenas gerencia o FakeRepository em RAM e registra chamadas de commit.
    """
    def __init__(self):
        self.families = FakeFamilyRepository()
        self.family_cost_centers = FakeFamilyCostCenterRepository()
        self.committed = False

    def __enter__(self):
        return super().__enter__()

    def commit(self):
        self.committed = True

    def rollback(self):
        pass
