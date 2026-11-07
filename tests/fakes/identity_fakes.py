import uuid
from datetime import datetime, timedelta
from typing import Optional

from application.interfaces.email_sender import AbstractEmailSender, EmailDeliveryError
from application.interfaces.link_builder import AbstractLinkBuilder
from application.interfaces.password_hasher import AbstractPasswordHasher
from domain.identity.entities import Role, User
from domain.identity.invitations import Invitation
from domain.identity.repositories import InvitationRepository, UserRepository
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

    def get_by_role(self, role: Role) -> Optional[User]:
        return next((u for u in self.users.values() if u.role is role), None)

    def list_all(self) -> list[User]:
        return list(self.users.values())

    def list_page(self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
                  search=None, family_id=None) -> Page:
        if sort_by not in ("name", "username", "email"):
            raise ValueError(f"Campo de ordenação inválido: {sort_by!r}.")
        found = [
            u for u in self.users.values()
            if (family_id is None or u.family_id == family_id)
            and (not search or any(fold_text(search) in fold_text(getattr(u, f)) for f in ("name", "username", "email")))
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


class FakeInvitationRepository(InvitationRepository):
    """Mesma semântica do repositório real, em memória (inclusive o consumo condicional)."""

    def __init__(self):
        self.invitations: dict[uuid.UUID, Invitation] = {}

    def save(self, invitation: Invitation) -> None:
        self.invitations[invitation.id] = invitation

    def get_by_token_hash(self, token_hash: str) -> Optional[Invitation]:
        return next((i for i in self.invitations.values() if i.token_hash == token_hash), None)

    def get_active_for_user(self, user_id: uuid.UUID) -> Optional[Invitation]:
        return next(
            (i for i in self.invitations.values()
             if i.user_id == user_id and i.consumed_at is None and i.revoked_at is None),
            None,
        )

    def revoke_active_for_user(self, user_id: uuid.UUID, now: datetime) -> None:
        for invitation in self.invitations.values():
            if invitation.user_id == user_id and invitation.consumed_at is None and invitation.revoked_at is None:
                invitation.revoked_at = now

    def register_failed_attempt(self, invitation_id: uuid.UUID) -> None:
        self.invitations[invitation_id].attempts += 1

    def consume(self, invitation_id: uuid.UUID, now: datetime, max_attempts: int) -> bool:
        invitation = self.invitations.get(invitation_id)
        if invitation is None or not invitation.is_usable(now, max_attempts):
            return False
        invitation.consumed_at = now
        return True

    def delete_for_user(self, user_id: uuid.UUID) -> None:
        for key in [k for k, i in self.invitations.items() if i.user_id == user_id]:
            del self.invitations[key]


class FakePasswordHasher(AbstractPasswordHasher):
    """Hash previsível e barato, só para os testes de serviço (o real é testado na infraestrutura).

    Registra as conferências para os testes poderem afirmar que o hash FOI conferido (ex.: contra o hash falso
    quando o usuário não existe)."""

    def __init__(self):
        self.verified: list[tuple[str, str]] = []
        self.outdated: set[str] = set()

    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        self.verified.append((password, password_hash))
        return password_hash == self.hash(password)

    def needs_rehash(self, password_hash: str) -> bool:
        return password_hash in self.outdated


class FakeEmailSender(AbstractEmailSender):
    """Caixa de saída em memória. `fail = True` simula o servidor de e-mail fora do ar."""

    def __init__(self):
        self.outbox: list[dict] = []
        self.fail = False

    def send(self, to: str, subject: str, body: str) -> None:
        if self.fail:
            raise EmailDeliveryError("servidor de e-mail indisponível")
        self.outbox.append({"to": to, "subject": subject, "body": body})

    @property
    def last(self) -> dict:
        return self.outbox[-1]

    def to(self, address: str) -> list[dict]:
        return [m for m in self.outbox if m["to"].lower() == address.lower()]


class FakeLinkBuilder(AbstractLinkBuilder):
    BASE = "https://app.test"

    def invitation_link(self, token: str) -> str:
        return f"{self.BASE}/auth/activate/{token}"

    def recovery_link(self, token: str) -> str:
        return f"{self.BASE}/auth/recover/{token}"


class FakeClock:
    """Relógio controlável: os testes de validade andam no tempo sem esperar."""

    def __init__(self, start: Optional[datetime] = None):
        self.now = start or datetime(2026, 11, 8, 12, 0, 0)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now += timedelta(**kwargs)


def token_from_link(text: str) -> str:
    """Extrai o token do último link /auth/... de um corpo de e-mail."""
    import re
    return re.findall(r"/auth/(?:activate|recover)/([A-Za-z0-9_-]+)", text)[-1]
