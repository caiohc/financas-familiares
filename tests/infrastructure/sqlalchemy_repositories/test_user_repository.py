import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from domain.identity.entities import Role, User
from domain.shared.exceptions import EntityAlreadyExistsError
from infrastructure.database.models import Base, FamilyModel
from infrastructure.repositories.sqlalchemy.sqlalchemy_user_repository import SQLAlchemyUserRepository


@pytest.fixture
def repo(session: Session) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(session)


@pytest.fixture
def family_id(session: Session) -> uuid.UUID:
    model = FamilyModel(id=str(uuid.uuid4()), name="Silva")
    session.add(model)
    session.flush()
    return uuid.UUID(model.id)


def _admin(**overrides) -> User:
    data = dict(role=Role.SYSTEM_ADMIN, name="Caio", username="admin", email="admin@example.com", password_hash="hash")
    data.update(overrides)
    return User(**data)


def _family_user(family_id, **overrides) -> User:
    data = dict(
        role=Role.FAMILY_USER, family_id=family_id, name="João", username="joao", email="joao@example.com",
        password_hash="hash",
    )
    data.update(overrides)
    return User(**data)


def test_save_and_get_by_id_round_trips_every_attribute(repo, family_id):
    user = _family_user(family_id, role=Role.FAMILY_ADMIN, must_change_password=False)
    repo.save(user)

    assert repo.get_by_id(user.id) == user


def test_system_admin_round_trips_without_family(repo):
    admin = _admin()
    repo.save(admin)

    fetched = repo.get_by_id(admin.id)
    assert fetched.family_id is None
    assert fetched.role is Role.SYSTEM_ADMIN


def test_root_round_trips_without_name(repo):
    root = User(role=Role.ROOT, username="root", email="root@example.com", password_hash="hash")
    repo.save(root)

    fetched = repo.get_by_id(root.id)
    assert (fetched.role, fetched.name, fetched.family_id) == (Role.ROOT, None, None)


def test_save_updates_an_existing_user(repo, family_id):
    user = _family_user(family_id)
    repo.save(user)
    user.change_password("novo-hash")
    repo.save(user)

    fetched = repo.get_by_id(user.id)
    assert (fetched.password_hash, fetched.must_change_password) == ("novo-hash", False)


def test_get_by_id_unknown_returns_none(repo):
    assert repo.get_by_id(uuid.uuid4()) is None


def test_get_by_email_ignores_case(repo, family_id):
    user = _family_user(family_id, email="Joao@Example.com")
    repo.save(user)

    assert repo.get_by_email("joao@example.COM").id == user.id
    assert repo.get_by_email("outro@example.com") is None


def test_get_by_username_ignores_case(repo, family_id):
    user = _family_user(family_id, username="Joao")
    repo.save(user)

    assert repo.get_by_username("JOAO").id == user.id
    assert repo.get_by_username("maria") is None


def test_exists_with_role(repo, family_id):
    assert repo.exists_with_role(Role.ROOT) is False

    repo.save(_family_user(family_id, role=Role.FAMILY_ADMIN))
    repo.save(_admin())
    assert repo.exists_with_role(Role.ROOT) is False
    assert repo.exists_with_role(Role.FAMILY_ADMIN) is True
    assert repo.exists_with_role(Role.SYSTEM_ADMIN) is True

    repo.save(User(role=Role.ROOT, username="root", email="root@example.com", password_hash="hash"))
    assert repo.exists_with_role(Role.ROOT) is True


@pytest.fixture
def committed_family_id() -> tuple[Session, uuid.UUID]:
    """Banco próprio (não o compartilhado) para poder dar commit: o repositório faz rollback
    ao detectar a colisão, e o usuário original precisa já estar gravado, como em produção."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    family = FamilyModel(id=str(uuid.uuid4()), name="Silva")
    session.add(family)
    session.commit()
    yield session, uuid.UUID(family.id)
    session.close()
    engine.dispose()


def test_duplicate_username_raises_domain_error(committed_family_id):
    session, family_id = committed_family_id
    repo = SQLAlchemyUserRepository(session)
    repo.save(_family_user(family_id, username="Joao", email="a@example.com"))
    session.commit()

    with pytest.raises(EntityAlreadyExistsError) as exc:
        repo.save(_family_user(family_id, username="joao", email="b@example.com"))

    assert exc.value.field == "username"


def test_duplicate_email_raises_domain_error(committed_family_id):
    session, family_id = committed_family_id
    repo = SQLAlchemyUserRepository(session)
    repo.save(_family_user(family_id, username="a", email="Joao@example.com"))
    session.commit()

    with pytest.raises(EntityAlreadyExistsError) as exc:
        repo.save(_family_user(family_id, username="b", email="joao@example.com"))

    assert exc.value.field == "email"
