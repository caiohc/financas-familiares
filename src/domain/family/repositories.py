from abc import ABC, abstractmethod
from domain.family.entities import Family, Member, FamilyCostCenter
from typing import Optional
import uuid

from domain.shared.pagination import Page

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
    def list_page(
        self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
        search: Optional[str] = None,
    ) -> Page[Family]:
        """Fatia (página 1-based) com o total geral, ordenada por um campo sem diferenciar maiúsculas; empates por nome e id.

        `search` filtra por trecho do nome (e, em membros e centros de custo, do nome da família),
        sem diferenciar caixa nem acentos; o total e a paginação valem sobre o resultado filtrado.
        """
        pass

    @abstractmethod
    def delete(self, family_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    def has_dependencies(self, family_id: uuid.UUID) -> bool:
        pass


class MemberRepository(ABC):
    """Interface para gerenciar Membros. Nome é único por família, não globalmente."""
    @abstractmethod
    def save(self, member: Member) -> None:
        pass

    @abstractmethod
    def get_by_id(self, member_id: uuid.UUID) -> Optional[Member]:
        pass

    @abstractmethod
    def get_by_name(self, family_id: uuid.UUID, name: str) -> Optional[Member]:
        """Busca case-insensitive, escopada à família (o mesmo nome pode existir em outra família)."""
        pass

    @abstractmethod
    def list_by_family(self, family_id: uuid.UUID) -> list[Member]:
        pass

    @abstractmethod
    def list_all(self) -> list[Member]:
        pass

    @abstractmethod
    def list_page(
        self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
        search: Optional[str] = None,
    ) -> Page[Member]:
        """Fatia (página 1-based) com o total geral, ordenada por um campo sem diferenciar maiúsculas; empates por nome e id.

        `search` filtra por trecho do nome (e, em membros e centros de custo, do nome da família),
        sem diferenciar caixa nem acentos; o total e a paginação valem sobre o resultado filtrado.
        """
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
    def list_all(self) -> list[FamilyCostCenter]:
        """
        Provisório: lista todos os centros de custo, cruzando famílias.
        Existe só porque a interface web ainda não tem autenticação/sessão de
        usuário para resolver "a família do usuário atual" (ver decisão do
        item de menu). Revisitar quando login existir.
        """
        pass

    @abstractmethod
    def list_page(
        self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
        search: Optional[str] = None,
    ) -> Page[FamilyCostCenter]:
        """Fatia (página 1-based) com o total geral, ordenada por um campo sem diferenciar maiúsculas; empates por nome e id.

        `search` filtra por trecho do nome (e, em membros e centros de custo, do nome da família),
        sem diferenciar caixa nem acentos; o total e a paginação valem sobre o resultado filtrado.
        """
        pass

    @abstractmethod
    def delete(self, cost_center_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    def has_dependencies(self, cost_center_id: uuid.UUID) -> bool:
        pass