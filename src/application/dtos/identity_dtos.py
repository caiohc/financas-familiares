import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.identity.entities import AccountStatus, Role
from domain.identity.invitations import InvitationPurpose
from domain.identity.policy import Principal


@dataclass(kw_only=True)
class CreateRootDTO:
    """Entrada da CLI. O root escolhe a própria senha no terminal (digitada duas vezes)."""
    username: str
    email: str
    password: str
    password_confirmation: Optional[str]


@dataclass(kw_only=True)
class CreateUserDTO:
    """Cadastro de usuário por um administrador. O administrador NÃO define senha: o usuário a define
    por um convite. O root não é criado por aqui (ver create-root)."""
    role: Optional[Role]
    family_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    username: str
    email: str
    email_confirmation: Optional[str]


@dataclass(kw_only=True)
class UpdateUserDTO:
    """Papel, família, senha e situação da conta não mudam por aqui."""
    name: Optional[str] = None
    username: str
    email: str


@dataclass(kw_only=True)
class UserResponseDTO:
    id: uuid.UUID
    role: Role
    family_id: Optional[uuid.UUID]
    name: Optional[str]
    username: str
    email: str
    status: AccountStatus
    is_active: bool
    # Nunca ativada: enquanto for verdade, o e-mail ainda pode ser corrigido por um administrador.
    is_pending: bool


@dataclass(kw_only=True)
class InvitationIssuedDTO:
    """Resultado de emitir um convite. O código só existe aqui, nesta resposta: não fica guardado em
    texto em lugar nenhum e não pode ser consultado depois (só reemitindo o convite)."""
    user: UserResponseDTO
    purpose: InvitationPurpose
    code: str
    expires_at: datetime
    email_sent: bool


@dataclass(kw_only=True)
class InvitationInfoDTO:
    """O que a página do link precisa saber. Não revela nada sobre o usuário."""
    purpose: InvitationPurpose
    requires_code: bool


@dataclass(kw_only=True)
class SessionUserDTO:
    """O usuário autenticado, como a camada web o conhece. Sem hash de senha."""
    id: uuid.UUID
    role: Role
    family_id: Optional[uuid.UUID]
    name: Optional[str]
    username: str
    email: str
    # Identificador guardado no cookie: "id:versão-da-credencial". Muda quando a senha muda.
    session_id: str

    @property
    def principal(self) -> Principal:
        return Principal(user_id=self.id, role=self.role, family_id=self.family_id)

    @property
    def display_name(self) -> str:
        return self.name or self.username
