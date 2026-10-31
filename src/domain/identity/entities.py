"""
Subdomínio de Autenticação e Autorização (Identidade)
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional

from domain.shared.exceptions import DomainValidationError


def _required(value: Optional[str], field_name: str, error_message: str) -> str:
    if not value or not value.strip():
        raise DomainValidationError(field_name, error_message)
    return value.strip()


@dataclass(kw_only=True)
class User:
    """Entidade de sistema voltada especificamente para Autenticação e Autorização.

    O tenant é a Família: todo usuário pertence a uma família, exceto os usuários
    administradores, que não são vinculados a nenhuma (family_id é None).
    `username` e `email` são únicos em toda a aplicação (unicidade global, cada um
    individualmente), garantida pela infraestrutura de persistência.
    """
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: Optional[uuid.UUID] = None  # None => usuário administrador (sem família)
    username: str
    email: str

    # Exemplo: atributos de segurança, hashes de senha e parâmetros de permissões
    # pertenceriam exclusivamente à lógica deste subdomínio.

    @staticmethod
    def normalize_username(username: Optional[str]) -> str:
        return _required(username, "username", "Nome de usuário é obrigatório.")

    @staticmethod
    def normalize_email(email: Optional[str]) -> str:
        return _required(email, "email", "E-mail é obrigatório.")

    def __post_init__(self):
        self.username = self.normalize_username(self.username)
        self.email = self.normalize_email(self.email)
