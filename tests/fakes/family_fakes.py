import uuid

from domain.shared.pagination import Page
from domain.shared.text import fold_text
from typing import Optional
from domain.family.repositories import FamilyRepository, FamilyCostCenterRepository, MemberRepository
from domain.family.entities import Family, FamilyCostCenter, Member
from application.interfaces.unit_of_work import AbstractUnitOfWork
from fakes.financial_fakes import FakeCategoryRepository
from fakes.identity_fakes import FakeInvitationRepository, FakeUserRepository


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

    def list_page(self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
                  search=None) -> Page:
        if sort_by != "name":
            raise ValueError(f"Campo de ordenação inválido: {sort_by!r}.")
        found = [e for e in self.families.values() if not search or fold_text(search) in fold_text(e.name)]
        ordered = sorted(found, key=lambda e: str(e.id))
        ordered = sorted(ordered, key=lambda e: e.name.lower(), reverse=descending)
        start = (page - 1) * page_size
        return Page(items=ordered[start:start + page_size], total=len(ordered))

    def delete(self, family_id: uuid.UUID) -> None:
        if family_id in self.families:
            del self.families[family_id]

    def has_dependencies(self, family_id: uuid.UUID) -> bool:
        return self._has_deps

    def set_has_dependencies(self, value: bool):
        """Método auxiliar exclusivo para testes manipularem o estado do Fake."""
        self._has_deps = value


class FakeMemberRepository(MemberRepository):
    """
    Fake Repository centralizado para testes.
    Armazena os dados em memória RAM usando um dicionário.
    """
    def __init__(self, families=None):
        self._families = families
        self.members = {}
        self._has_deps = False

    def save(self, member: Member) -> None:
        self.members[member.id] = member

    def get_by_id(self, member_id: uuid.UUID) -> Optional[Member]:
        return self.members.get(member_id)

    def get_by_name(self, family_id: uuid.UUID, name: str) -> Optional[Member]:
        for member in self.members.values():
            if member.family_id == family_id and member.name.lower() == name.lower():
                return member
        return None

    def list_by_family(self, family_id: uuid.UUID) -> list[Member]:
        return [m for m in self.members.values() if m.family_id == family_id]

    def list_all(self) -> list[Member]:
        return list(self.members.values())

    def _family_name(self, entity) -> str:
        family = self._families.get_by_id(entity.family_id) if self._families else None
        return fold_text(family.name) if family else ""

    def list_page(self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
                  search=None) -> Page:
        if sort_by not in ("name", "family"):
            raise ValueError(f"Campo de ordenação inválido: {sort_by!r}.")
        found = [
            e for e in self.members.values()
            if not search or fold_text(search) in fold_text(e.name) or fold_text(search) in self._family_name(e)
        ]
        ordered = sorted(found, key=lambda e: str(e.id))
        ordered = sorted(ordered, key=lambda e: e.name.lower(), reverse=(sort_by == "name" and descending))
        if sort_by == "family":
            ordered = sorted(ordered, key=self._family_name, reverse=descending)
        start = (page - 1) * page_size
        return Page(items=ordered[start:start + page_size], total=len(ordered))

    def delete(self, member_id: uuid.UUID) -> None:
        if member_id in self.members:
            del self.members[member_id]

    def has_dependencies(self, member_id: uuid.UUID) -> bool:
        return self._has_deps

    def set_has_dependencies(self, value: bool):
        """Método auxiliar exclusivo para testes manipularem o estado do Fake."""
        self._has_deps = value


class FakeFamilyCostCenterRepository(FamilyCostCenterRepository):
    """
    Fake Repository centralizado para testes.
    Armazena os dados em memória RAM usando um dicionário.
    """
    def __init__(self, families=None):
        self._families = families
        self.cost_centers = {}
        self._has_deps = False

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

    def list_all(self) -> list[FamilyCostCenter]:
        return list(self.cost_centers.values())

    def _family_name(self, entity) -> str:
        family = self._families.get_by_id(entity.family_id) if self._families else None
        return fold_text(family.name) if family else ""

    def list_page(self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
                  search=None) -> Page:
        if sort_by not in ("name", "family"):
            raise ValueError(f"Campo de ordenação inválido: {sort_by!r}.")
        found = [
            e for e in self.cost_centers.values()
            if not search or fold_text(search) in fold_text(e.name) or fold_text(search) in self._family_name(e)
        ]
        ordered = sorted(found, key=lambda e: str(e.id))
        ordered = sorted(ordered, key=lambda e: e.name.lower(), reverse=(sort_by == "name" and descending))
        if sort_by == "family":
            ordered = sorted(ordered, key=self._family_name, reverse=descending)
        start = (page - 1) * page_size
        return Page(items=ordered[start:start + page_size], total=len(ordered))

    def delete(self, cost_center_id: uuid.UUID) -> None:
        if cost_center_id in self.cost_centers:
            del self.cost_centers[cost_center_id]

    def has_dependencies(self, cost_center_id: uuid.UUID) -> bool:
        return self._has_deps

    def set_has_dependencies(self, value: bool):
        """Método auxiliar exclusivo para testes manipularem o estado do Fake."""
        self._has_deps = value


class FakeUnitOfWork(AbstractUnitOfWork):
    """
    Fake UnitOfWork para testes.
    Apenas gerencia o FakeRepository em RAM e registra chamadas de commit.
    """
    def __init__(self):
        self.families = FakeFamilyRepository()
        self.members = FakeMemberRepository(self.families)
        self.family_cost_centers = FakeFamilyCostCenterRepository(self.families)
        self.categories = FakeCategoryRepository()
        self.users = FakeUserRepository()
        self.invitations = FakeInvitationRepository()
        self.committed = False

    def __enter__(self):
        return super().__enter__()

    def commit(self):
        self.committed = True

    def rollback(self):
        pass
