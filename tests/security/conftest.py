"""
Fixtures dos testes de SEGURANÇA: a aplicação real (serviços, banco, Argon2 de teste, Flask-Login, CSRF, limites),
com a proteção de rotas LIGADA e um servidor de e-mail falso para ler os links enviados.
"""
import re
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.identity.entities import Role
from fakes.identity_fakes import FakeEmailSender
from interface.web.security import limiter
from support import STRONG_PASSWORD, create_test_app, insert_user

CSRF_INPUT = re.compile(r'name="csrf_token" value="([^"]+)"')


def reset_limiter() -> None:
    """Zera os contadores de tentativas (o limitador é um objeto único, compartilhado entre os testes)."""
    if getattr(limiter, "_storage", None) is not None:
        limiter.reset()


class World:
    """O ambiente de um teste: a aplicação, a caixa de saída de e-mail e atalhos para criar gente e entrar."""

    def __init__(self, app, emails: FakeEmailSender):
        self.app = app
        self.emails = emails
        self._engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        self._maker = sessionmaker(bind=self._engine)

    def add_family(self, name: str = "Família Teste") -> uuid.UUID:
        from infrastructure.database.models import FamilyModel

        with self._maker() as session:
            family = FamilyModel(id=str(uuid.uuid4()), name=name)
            session.add(family)
            session.commit()
            return uuid.UUID(family.id)

    def add_user(self, username: str, role: Role = Role.FAMILY_USER, family_id=None, **kwargs) -> uuid.UUID:
        if role in (Role.FAMILY_ADMIN, Role.FAMILY_USER) and family_id is None:
            family_id = self.add_family(f"Família de {username}")
        with self._maker() as session:
            return insert_user(session, role=role, username=username, family_id=family_id, **kwargs)

    def client(self):
        return self.app.test_client()

    def login(self, client, username: str, password: str = STRONG_PASSWORD, follow: bool = False, **extra):
        return client.post(
            "/auth/authenticate", data={"identifier": username, "password": password, **extra}, follow_redirects=follow,
        )

    def logged(self, username: str, password: str = STRONG_PASSWORD):
        client = self.client()
        response = self.login(client, username, password)
        assert response.status_code == 302, f"login de {username} falhou: {response.status_code}"
        return client

    def user_row(self, username: str):
        from infrastructure.database.models import UserModel

        with self._maker() as session:
            session.expire_on_commit = False
            return session.query(UserModel).filter(UserModel.username == username).one()

    def dispose(self):
        self._engine.dispose()


def csrf_token_from(html: str) -> str:
    match = CSRF_INPUT.search(html)
    assert match, "formulário sem csrf_token"
    return match.group(1)


@pytest.fixture
def make_world(tmp_path):
    """Fábrica de ambientes: `make_world(CONFIG=...)`. Por padrão, proteção LIGADA, CSRF e limites desligados
    (os testes específicos os ligam)."""
    created = []

    def _make(subdir=None, **config):
        """`subdir` isola o banco quando um teste precisa de dois ambientes ao mesmo tempo."""
        folder = tmp_path / subdir if subdir else tmp_path
        folder.mkdir(exist_ok=True)
        reset_limiter()
        app = create_test_app(folder, AUTH_ENABLED=True, with_dev_user=False, **config)
        emails = FakeEmailSender()
        app.extensions["email_sender"] = emails
        world = World(app, emails)
        created.append(world)
        return world

    yield _make
    for world in created:
        world.dispose()
    reset_limiter()


@pytest.fixture
def world(make_world):
    return make_world()
