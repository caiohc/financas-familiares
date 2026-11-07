"""
Subdomínio de Autenticação e Autorização (Identidade)
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from domain.identity.exceptions import (
    family_required_for_role,
    family_not_allowed_for_system_roles,
)
from domain.shared.exceptions import DomainValidationError

MIN_PASSWORD_LENGTH = 8


class Role(Enum):
    ROOT = "ROOT"                  # Usuário inicial, criado pela CLI. Não representa uma pessoa (sem nome). Sem família.
    SYSTEM_ADMIN = "SYSTEM_ADMIN"  # Administra o sistema: cadastra famílias e usuários. Pessoa identificada. Sem família.
    FAMILY_ADMIN = "FAMILY_ADMIN"  # Administra uma família (tenant): cadastra membros, centros de custo etc.
    FAMILY_USER = "FAMILY_USER"    # Opera o sistema dentro de uma família. Sem vínculo com Member.


# Papéis de nível de sistema: não pertencem a nenhuma família.
SYSTEM_LEVEL_ROLES = frozenset({Role.ROOT, Role.SYSTEM_ADMIN})


def _required(value: Optional[str], field_name: str, error_message: str) -> str:
    if not value or not value.strip():
        raise DomainValidationError(field_name, error_message)
    return value.strip()


@dataclass(kw_only=True)
class User:
    """Entidade de sistema voltada especificamente para Autenticação e Autorização.

    O tenant é a Família: todo usuário pertence a uma família, exceto os de nível de
    sistema (`Role.ROOT` e `Role.SYSTEM_ADMIN`), que não são vinculados a nenhuma.
    Invariantes:
    - `family_id` é None se e somente se `role` for ROOT ou SYSTEM_ADMIN;
    - `name` (da pessoa) é obrigatório para todos, exceto ROOT, que não representa
      uma pessoa e pode ficar sem nome (None).
    `username` e `email` são únicos em toda a aplicação (unicidade global, cada um
    individualmente), garantida pela infraestrutura de persistência.

    O usuário não tem relação com Member: pode nem pertencer à família na vida real.
    `password_hash` é opaco para o domínio; quem calcula e confere o hash é a
    infraestrutura (ver application/interfaces/password_hasher.py). Senhas definidas
    por um administrador são temporárias: `must_change_password` obriga a troca.
    """
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    role: Role
    family_id: Optional[uuid.UUID] = None  # None <=> ROOT ou SYSTEM_ADMIN
    name: Optional[str] = None  # Nome da pessoa; só o ROOT pode não ter
    username: str
    email: str
    password_hash: str
    must_change_password: bool = True

    @staticmethod
    def normalize_username(username: Optional[str]) -> str:
        return _required(username, "username", "Nome de usuário é obrigatório.")

    @staticmethod
    def normalize_name(name: Optional[str], role: Role) -> Optional[str]:
        if role is Role.ROOT:
            return name.strip() or None if name else None
        return _required(name, "name", "Nome é obrigatório.")

    @staticmethod
    def normalize_email(email: Optional[str]) -> str:
        return _required(email, "email", "E-mail é obrigatório.")

    @staticmethod
    def validate_role(role: Optional[Role]) -> Role:
        if not isinstance(role, Role):
            raise DomainValidationError("role", "Papel do usuário é obrigatório.")
        return role

    @staticmethod
    def validate_family_for_role(role: Role, family_id: Optional[uuid.UUID]) -> Optional[uuid.UUID]:
        if role in SYSTEM_LEVEL_ROLES:
            if family_id is not None:
                raise family_not_allowed_for_system_roles()
        elif family_id is None:
            raise family_required_for_role()
        return family_id

    @staticmethod
    def validate_raw_password(password: Optional[str]) -> str:
        """Política mínima de senha, aplicada antes do hash (o hash em si não revela o tamanho)."""
        if not password or not password.strip():
            raise DomainValidationError("password", "Senha é obrigatória.")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise DomainValidationError(
                "password", f"A senha deve ter pelo menos {MIN_PASSWORD_LENGTH} caracteres."
            )
        return password

    @staticmethod
    def validate_password_confirmation(password: str, confirmation: Optional[str]) -> None:
        """A senha digitada duas vezes precisa ser idêntica (comparação exata, sem ignorar espaços ou caixa)."""
        if confirmation != password:
            raise DomainValidationError("password_confirmation", "As senhas informadas não conferem.")

    @staticmethod
    def validate_password_hash(password_hash: Optional[str]) -> str:
        return _required(password_hash, "password", "Senha é obrigatória.")

    def __post_init__(self):
        self.role = self.validate_role(self.role)
        self.family_id = self.validate_family_for_role(self.role, self.family_id)
        self.name = self.normalize_name(self.name, self.role)
        self.username = self.normalize_username(self.username)
        self.email = self.normalize_email(self.email)
        self.password_hash = self.validate_password_hash(self.password_hash)

    @property
    def is_root(self) -> bool:
        return self.role is Role.ROOT

    @property
    def is_system_admin(self) -> bool:
        return self.role is Role.SYSTEM_ADMIN

    @property
    def is_family_admin(self) -> bool:
        return self.role is Role.FAMILY_ADMIN

    def update_profile(self, name: Optional[str], username: Optional[str], email: Optional[str]) -> None:
        """Altera os dados de identificação. Valida tudo antes de alterar, para não deixar a entidade pela metade."""
        new_name = self.normalize_name(name, self.role)
        new_username = self.normalize_username(username)
        new_email = self.normalize_email(email)
        self.name, self.username, self.email = new_name, new_username, new_email

    def set_temporary_password(self, password_hash: str) -> None:
        """Senha definida por um administrador: o usuário precisa trocá-la no próximo acesso."""
        self.password_hash = self.validate_password_hash(password_hash)
        self.must_change_password = True

    def change_password(self, password_hash: str) -> None:
        """Senha escolhida pelo próprio usuário: encerra a obrigação de troca."""
        self.password_hash = self.validate_password_hash(password_hash)
        self.must_change_password = False
