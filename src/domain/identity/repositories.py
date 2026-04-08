import uuid
from abc import ABC, abstractmethod
from typing import Optional

from domain.identity.entities import User


class UserRepository(ABC):
    """Interface abstrata (Contrato) que permite gravar o usuário mantendo o isolamento N -> 1 
       proposto em relação ao membro da família.
    """
    
    @abstractmethod
    def save(self, user: User) -> None:
        pass

    @abstractmethod
    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Contrato de busca de email fundamental para as rotas autônomas e lógicas de Login."""
        pass
