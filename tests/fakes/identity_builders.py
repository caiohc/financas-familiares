"""Construtores de dados de identidade para os testes de serviço (sobre os fakes em memória)."""
import itertools
import uuid
from typing import Optional

from domain.family.entities import Family
from domain.identity.entities import Role, User
from domain.identity.policy import Principal
from fakes.identity_fakes import FakePasswordHasher

PASSWORD = "senha-segura-123"
_counter = itertools.count(1)


def hashed(password: str) -> str:
    return FakePasswordHasher().hash(password)


def make_family(uow, name: Optional[str] = None) -> Family:
    family = Family(name=name or f"Família {next(_counter)}")
    uow.families.save(family)
    return family


def make_user(
    uow, role: Role = Role.FAMILY_USER, *, family: Optional[Family] = None, password: Optional[str] = PASSWORD,
    name: Optional[str] = None, username: Optional[str] = None, email: Optional[str] = None,
    active: bool = True, activated: bool = True,
) -> User:
    """Cria e grava um usuário. `activated=False` ou `password=None` geram uma conta pendente."""
    n = next(_counter)
    in_family = role in (Role.FAMILY_ADMIN, Role.FAMILY_USER)
    if in_family and family is None:
        family = make_family(uow)
    username = username or f"user{n}"
    user = User(
        role=role,
        family_id=family.id if in_family else None,
        name=None if role is Role.ROOT else (name or f"Pessoa {n}"),
        username=username,
        email=email or f"{username}@example.com",
        password_hash=hashed(password) if (password is not None and activated) else None,
        is_active=active,
    )
    uow.users.save(user)
    return user


def principal_of(user: User) -> Principal:
    return Principal(user_id=user.id, role=user.role, family_id=user.family_id)


def outsider(role: Role, family_id: Optional[uuid.UUID] = None) -> Principal:
    """Ator que não existe no banco (para casos em que só a política importa)."""
    return Principal(user_id=uuid.uuid4(), role=role, family_id=family_id)
