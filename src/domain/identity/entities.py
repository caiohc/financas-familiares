"""
Subdomínio de Autenticação e Autorização (Identidade)
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from email_validator import EmailNotValidError, validate_email

from domain.identity.exceptions import (
    cannot_deactivate_root,
    email_invalid,
    email_locked_after_activation,
    email_confirmation_mismatch,
    family_required_for_role,
    family_not_allowed_for_system_roles,
    root_requires_password,
)
from domain.shared.clock import utcnow
from domain.shared.exceptions import DomainValidationError

MIN_PASSWORD_LENGTH = 8


class Role(Enum):
    ROOT = "ROOT"                  # Usuário inicial, criado pela CLI. Não representa uma pessoa (sem nome). Sem família.
    SYSTEM_ADMIN = "SYSTEM_ADMIN"  # Administra o sistema: cadastra famílias e usuários. Pessoa identificada. Sem família.
    FAMILY_ADMIN = "FAMILY_ADMIN"  # Administra uma família (tenant): cadastra membros, centros de custo etc.
    FAMILY_USER = "FAMILY_USER"    # Opera o sistema dentro de uma família. Sem vínculo com Member.


# Papéis de nível de sistema: não pertencem a nenhuma família.
SYSTEM_LEVEL_ROLES = frozenset({Role.ROOT, Role.SYSTEM_ADMIN})


class AccountStatus(Enum):
    PENDING = "PENDING"                      # nunca ativada: sem senha; o e-mail ainda não é confiável
    AWAITING_PASSWORD = "AWAITING_PASSWORD"  # já ativada, mas a senha foi revogada por redefinição administrativa
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"


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
      uma pessoa e pode ficar sem nome (None);
    - o ROOT sempre tem senha (é criado pela CLI, com a senha digitada no terminal);
    - quem tem senha tem data de ativação (`activated_at`).
    `username` e `email` são únicos em toda a aplicação (unicidade global, cada um
    individualmente), garantida pela infraestrutura de persistência.

    O usuário não tem relação com Member: pode nem pertencer à família na vida real.
    `password_hash` é opaco para o domínio (quem calcula e confere o hash é a
    infraestrutura, ver application/interfaces/password_hasher.py) e é None enquanto
    a pessoa não definiu a senha. Ninguém além da própria pessoa conhece a senha:
    o administrador só emite um convite (link por e-mail + código por outro canal).

    Ciclo de vida: PENDING (sem senha, nunca ativada) -> ACTIVE (senha definida pelo
    convite) -> AWAITING_PASSWORD (redefinição administrativa revogou a senha) -> ACTIVE.
    `is_active` False desativa a conta em qualquer estágio, sem apagar os dados.
    """
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    role: Role
    family_id: Optional[uuid.UUID] = None  # None <=> ROOT ou SYSTEM_ADMIN
    name: Optional[str] = None  # Nome da pessoa; só o ROOT pode não ter
    username: str
    email: str
    password_hash: Optional[str] = None
    is_active: bool = True
    activated_at: Optional[datetime] = None

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
        text = _required(email, "email", "E-mail é obrigatório.")
        try:
            # Só o formato: sem consulta de DNS (check_deliverability), que seria E/S no domínio.
            return validate_email(text, check_deliverability=False).normalized
        except EmailNotValidError:
            raise email_invalid()

    @staticmethod
    def validate_email_confirmation(email: Optional[str], confirmation: Optional[str]) -> None:
        """O e-mail digitado duas vezes precisa coincidir (sem diferenciar caixa nem espaços nas pontas)."""
        if (email or "").strip().casefold() != (confirmation or "").strip().casefold():
            raise email_confirmation_mismatch()

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
        if self.password_hash is not None:
            self.password_hash = self.validate_password_hash(self.password_hash)
            # Quem já chega com senha foi ativado (ex.: o root criado pela CLI).
            if self.activated_at is None:
                self.activated_at = utcnow()
        elif self.role is Role.ROOT:
            raise root_requires_password()

    # --- Consultas ---

    @property
    def is_root(self) -> bool:
        return self.role is Role.ROOT

    @property
    def is_system_admin(self) -> bool:
        return self.role is Role.SYSTEM_ADMIN

    @property
    def is_family_admin(self) -> bool:
        return self.role is Role.FAMILY_ADMIN

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None

    @property
    def is_pending(self) -> bool:
        """Nunca ativou a conta: o e-mail é só o que o administrador digitou."""
        return self.activated_at is None

    @property
    def can_authenticate(self) -> bool:
        return self.is_active and self.has_password

    @property
    def status(self) -> AccountStatus:
        if not self.is_active:
            return AccountStatus.DEACTIVATED
        if self.is_pending:
            return AccountStatus.PENDING
        if not self.has_password:
            return AccountStatus.AWAITING_PASSWORD
        return AccountStatus.ACTIVE

    # --- Alterações ---

    def update_profile(self, name: Optional[str], username: Optional[str], email: Optional[str]) -> None:
        """Edição administrativa. Valida tudo antes de alterar, para não deixar a entidade pela metade.

        Depois da ativação o e-mail é confiável (a pessoa provou controlar a caixa) e é o canal
        de recuperação da senha: nenhum administrador pode mais trocá-lo, senão bastaria trocar
        o e-mail e pedir a recuperação para tomar a conta.
        """
        new_name = self.normalize_name(name, self.role)
        new_username = self.normalize_username(username)
        new_email = self.normalize_email(email)
        if not self.is_pending and new_email.casefold() != self.email.casefold():
            raise email_locked_after_activation()
        self.name, self.username, self.email = new_name, new_username, new_email

    def change_email(self, email: Optional[str]) -> None:
        """Troca do e-mail por quem tem esse direito: o próprio usuário ou, no caso do root, quem executa a CLI no
        servidor. Diferente de `update_profile` (edição administrativa), não é barrada pela trava pós-ativação."""
        self.email = self.normalize_email(email)

    def define_password(self, password_hash: str, now: Optional[datetime] = None) -> None:
        """Senha definida pela própria pessoa, a partir de um convite (ativação ou redefinição)."""
        self.password_hash = self.validate_password_hash(password_hash)
        if self.activated_at is None:
            self.activated_at = now or utcnow()

    def change_password(self, password_hash: str) -> None:
        """Troca de senha pela própria pessoa (a autenticação da senha atual é do serviço)."""
        self.password_hash = self.validate_password_hash(password_hash)

    def revoke_password(self) -> None:
        """Redefinição administrativa: a senha atual deixa de valer até a pessoa definir outra."""
        if self.is_root:
            raise root_requires_password()
        self.password_hash = None

    def deactivate(self) -> None:
        if self.is_root:
            raise cannot_deactivate_root()
        self.is_active = False

    def reactivate(self) -> None:
        self.is_active = True
