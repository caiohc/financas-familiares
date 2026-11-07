import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from domain.identity.entities import Role, User
from domain.identity.invitations import Invitation
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
    def get_by_role(self, role: Role) -> Optional[User]:
        """Primeiro usuário do papel (útil para o ROOT, que é único)."""
        pass

    @abstractmethod
    def list_all(self) -> list[User]:
        pass

    @abstractmethod
    def list_page(
        self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
        search: Optional[str] = None, family_id: Optional[uuid.UUID] = None,
    ) -> Page[User]:
        """Fatia (página 1-based) com o total geral, ordenada por um campo (name, username ou email)
        sem diferenciar maiúsculas; empates por nome de usuário e id. Usuário sem nome (root) vem primeiro
        na ordem ascendente.

        `search` filtra por trecho do nome, do nome de usuário ou do e-mail, sem diferenciar caixa
        nem acentos; o total e a paginação valem sobre o resultado filtrado.
        `family_id`, quando informado, restringe a listagem aos usuários dessa família (escopo do tenant).
        """
        pass

    @abstractmethod
    def delete(self, user_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    def has_dependencies(self, user_id: uuid.UUID) -> bool:
        pass


class InvitationRepository(ABC):
    """Convites de ativação, redefinição e recuperação. Token e código ficam só em hash."""

    @abstractmethod
    def save(self, invitation: Invitation) -> None:
        pass

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> Optional[Invitation]:
        pass

    @abstractmethod
    def get_active_for_user(self, user_id: uuid.UUID) -> Optional[Invitation]:
        """O convite não consumido e não revogado do usuário (no máximo um), vencido ou não."""
        pass

    @abstractmethod
    def revoke_active_for_user(self, user_id: uuid.UUID, now: datetime) -> None:
        """Emitir um convite novo revoga o anterior."""
        pass

    @abstractmethod
    def register_failed_attempt(self, invitation_id: uuid.UUID) -> None:
        """Soma uma tentativa errada de código de forma atômica (sem ler e regravar)."""
        pass

    @abstractmethod
    def consume(self, invitation_id: uuid.UUID, now: datetime, max_attempts: int) -> bool:
        """Consome o convite de forma ATÔMICA: só um chamador consegue, mesmo em requisições
        simultâneas. Falha (False) se já foi usado, revogado, venceu ou estourou as tentativas."""
        pass

    @abstractmethod
    def delete_for_user(self, user_id: uuid.UUID) -> None:
        pass
