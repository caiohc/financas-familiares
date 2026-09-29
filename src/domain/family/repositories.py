from abc import ABC, abstractmethod
from domain.family.entities import Family, Member, FamilyCostCenter
from typing import Optional
import uuid

class FamilyRepository(ABC):
    """Interface (Contrato) para operações de banco de dados com Famílias."""
    @abstractmethod
    def save(self, family: Family) -> None:
        pass

    @abstractmethod
    def get_by_id(self, family_id: uuid.UUID) -> Optional[Family]:
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Family]:
        """Busca case-insensitive: nome é único independente de maiúsculas/minúsculas."""
        pass

    @abstractmethod
    def list_all(self) -> list[Family]:
        pass

    @abstractmethod
    def delete(self, family_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    def has_dependencies(self, family_id: uuid.UUID) -> bool:
        pass


class MemberRepository(ABC):
    """Interface para gerenciar Membros. O contexto financeiro dita as buscas atreladas à Família."""
    @abstractmethod
    def save(self, member: Member) -> None:
        pass

    @abstractmethod
    def get_by_id(self, member_id: uuid.UUID) -> Optional[Member]:
        pass

    @abstractmethod
    def list_by_family(self, family_id: uuid.UUID) -> list[Member]:
        pass

    @abstractmethod
    def list_all(self) -> list[Member]:
        pass

    @abstractmethod
    def delete(self, member_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    def has_dependencies(self, member_id: uuid.UUID) -> bool:
        pass


class FamilyCostCenterRepository(ABC):
    """Interface para gerenciar Centros de Custo. Nome é único por família, não globalmente."""
    @abstractmethod
    def save(self, cost_center: FamilyCostCenter) -> None:
        pass

    @abstractmethod
    def get_by_id(self, cost_center_id: uuid.UUID) -> Optional[FamilyCostCenter]:
        pass

    @abstractmethod
    def get_by_name(self, family_id: uuid.UUID, name: str) -> Optional[FamilyCostCenter]:
        """Busca case-insensitive, escopada à família (o mesmo nome pode existir em outra família)."""
        pass

    @abstractmethod
    def list_by_family(self, family_id: uuid.UUID) -> list[FamilyCostCenter]:
        pass

    @abstractmethod
    def delete(self, cost_center_id: uuid.UUID) -> None:
        pass