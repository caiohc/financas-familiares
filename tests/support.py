"""
Apoio compartilhado pelos testes de aplicação completa (web e e2e).

BASE_APP_CONFIG liga o modo de desenvolvimento sem proteção (AUTH_ENABLED=false): a aplicação autentica
sozinha como o usuário DEV_USER, que as fixtures criam no banco. É o que permite aos testes de CRUD ignorar
o login. Os testes de SEGURANÇA (tests/security) ligam a proteção e exercitam o login de verdade.
"""
import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.identity.entities import Role
from infrastructure.database.models import Base, UserModel
from infrastructure.security.password_hasher import Argon2PasswordHasher

DEV_USER = "dev-admin"
STRONG_PASSWORD = "senha-segura-123"

BASE_APP_CONFIG = {
    "TESTING": True,
    "DEBUG": False,                   # o .env de quem desenvolve pode ligar FLASK_DEBUG (e o eco de SQL)
    "SECRET_KEY": "test-secret-key-only-for-tests-0123456789abcdef",
    "APP_ENV": "development",
    "AUTH_ENABLED": False,
    "DEV_AUTO_LOGIN_USERNAME": DEV_USER,
    "WTF_CSRF_ENABLED": False,        # os testes de CSRF o ligam explicitamente
    "RATELIMIT_ENABLED": False,       # os testes de limite o ligam explicitamente
    "PASSWORD_HASH_PROFILE": "test",  # Argon2id leve: a suíte não espera 64 MiB por hash
}

_HASHER = Argon2PasswordHasher("test")


def insert_user(
    session, *, role=Role.SYSTEM_ADMIN, username=DEV_USER, email=None, name="Administrador de Teste",
    family_id=None, password=STRONG_PASSWORD, is_active=True, activated=True,
) -> uuid.UUID:
    """Insere um usuário direto no banco, com senha real (hash de teste), sem passar pelos serviços."""
    user_id = uuid.uuid4()
    session.add(UserModel(
        id=str(user_id), role=role, family_id=str(family_id) if family_id else None,
        name=None if role is Role.ROOT else name, username=username,
        email=email or f"{username}@example.com",
        password_hash=_HASHER.hash(password) if password is not None else None,
        is_active=is_active,
        activated_at=datetime(2026, 1, 1) if activated else None,
    ))
    session.commit()
    return user_id


def create_database(tmp_path, with_dev_user: bool = True) -> str:
    """Cria o banco de teste em arquivo (com o usuário de desenvolvimento) e devolve a URI."""
    db_uri = f"sqlite:///{tmp_path / 'app_test.db'}"
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    if with_dev_user:
        with sessionmaker(bind=engine)() as session:
            insert_user(session)
    engine.dispose()
    return db_uri


def create_test_app(tmp_path, **config):
    """App real (fábricas de produção) com banco em arquivo e o usuário de desenvolvimento."""
    from app import create_app

    db_uri = create_database(tmp_path, with_dev_user=config.pop("with_dev_user", True))
    return create_app({**BASE_APP_CONFIG, "SQLALCHEMY_DATABASE_URI": db_uri, **config})


def assert_listing_call(paged_method, **expected) -> None:
    """Confere os argumentos de uma chamada paginada, ignorando `actor` (o usuário que age, que só
    a listagem de usuários recebe)."""
    paged_method.assert_called_once()
    kwargs = {k: v for k, v in paged_method.call_args.kwargs.items() if k != "actor"}
    assert kwargs == expected
