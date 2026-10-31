import uuid
from abc import ABC, abstractmethod
from typing import Optional

from domain.identity.entities import Role, User
from domain.shared.pagination import Page


class UserRepository(ABC):
    """Interface abstrata (Contrato) que permite gravar o usuário mantendo o isolamento N -> 1
       proposto em relação à família.
    """

    @abstractmethod
    def save(self, user: User) -> None:
        pass

    @abstractmethod
    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Contrato de busca de email fundamental para as rotas autônomas e lógicas de Login.
        Sem diferenciar maiúsculas de minúsculas."""
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        """Sem diferenciar maiúsculas de minúsculas."""
        pass

    @abstractmethod
    def exists_with_role(self, role: Role) -> bool:
        pass

    @abstractmethod
    def list_page(
        self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
        search: Optional[str] = None,
    ) -> Page[User]:
        """Fatia (página 1-based) com o total geral, ordenada por um campo (name, username ou email)
        sem diferenciar maiúsculas; empates por nome de usuário e id. Usuário sem nome (root) vem primeiro
        na ordem ascendente.

        `search` filtra por trecho do nome, do nome de usuário ou do e-mail, sem diferenciar caixa
        nem acentos; o total e a paginação valem sobre o resultado filtrado.
        """
        pass

    @abstractmethod
    def delete(self, user_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    def has_dependencies(self, user_id: uuid.UUID) -> bool:
        pass
