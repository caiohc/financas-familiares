import uuid
from typing import Optional

from application.interfaces.password_hasher import AbstractPasswordHasher
from domain.identity.entities import Role, User
from domain.identity.repositories import UserRepository
from domain.shared.pagination import Page
from domain.shared.text import fold_text


class FakeUserRepository(UserRepository):
    """
    Fake Repository centralizado para testes.
    Armazena os dados em memória RAM usando um dicionário.
    """
    def __init__(self):
        self.users = {}
        self._has_deps = False

    def save(self, user: User) -> None:
        self.users[user.id] = user

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.users.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return next((u for u in self.users.values() if u.email.lower() == email.lower()), None)

    def get_by_username(self, username: str) -> Optional[User]:
        return next((u for u in self.users.values() if u.username.lower() == username.lower()), None)

    def exists_with_role(self, role: Role) -> bool:
        return any(u.role is role for u in self.users.values())

    def list_all(self) -> list[User]:
        return list(self.users.values())

    def list_page(self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
                  search=None) -> Page:
        if sort_by not in ("name", "username", "email"):
            raise ValueError(f"Campo de ordenação inválido: {sort_by!r}.")
        found = [
            u for u in self.users.values()
            if not search or any(fold_text(search) in fold_text(getattr(u, f)) for f in ("name", "username", "email"))
        ]
        ordered = sorted(found, key=lambda u: (u.username.lower(), str(u.id)))
        ordered = sorted(ordered, key=lambda u: (getattr(u, sort_by) or "").lower(), reverse=descending)
        start = (page - 1) * page_size
        return Page(items=ordered[start:start + page_size], total=len(ordered))

    def delete(self, user_id: uuid.UUID) -> None:
        if user_id in self.users:
            del self.users[user_id]

    def has_dependencies(self, user_id: uuid.UUID) -> bool:
        return self._has_deps

    def set_has_dependencies(self, value: bool):
        """Método auxiliar exclusivo para testes manipularem o estado do Fake."""
        self._has_deps = value


class FakePasswordHasher(AbstractPasswordHasher):
    """Hash previsível e barato, só para os testes de serviço (o real é testado na infraestrutura)."""

    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == self.hash(password)
