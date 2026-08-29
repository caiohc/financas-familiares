from abc import ABC, abstractmethod
from domain.family.entities import Family, Member
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