import uuid
from dataclasses import dataclass
from typing import Optional

from domain.identity.entities import Role


@dataclass(kw_only=True)
class CreateRootDTO:
    username: str
    email: str
    temporary_password: str


@dataclass(kw_only=True)
class CreateUserDTO:
    """Cadastro de usuário por um administrador. O root não é criado por aqui (ver create-root)."""
    role: Optional[Role]
    family_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    username: str
    email: str
    temporary_password: str


@dataclass(kw_only=True)
class UpdateUserDTO:
    """Papel e família de um usuário não mudam; a senha também não é alterada por aqui."""
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
    must_change_password: bool
