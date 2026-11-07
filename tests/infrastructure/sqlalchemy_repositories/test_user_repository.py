import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from domain.identity.entities import AccountStatus, Role, User
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
    user = _family_user(family_id, role=Role.FAMILY_ADMIN, activated_at=datetime(2026, 3, 4, 5, 6, 7))
    repo.save(user)

    assert repo.get_by_id(user.id) == user


def test_a_pending_account_round_trips_without_password_and_activation(repo, family_id):
    pending = _family_user(family_id, password_hash=None)
    repo.save(pending)

    fetched = repo.get_by_id(pending.id)
    assert (fetched.password_hash, fetched.activated_at, fetched.status) == (None, None, AccountStatus.PENDING)


def test_an_account_awaiting_a_new_password_round_trips(repo):
    admin = _admin()
    admin.revoke_password()
    repo.save(admin)

    fetched = repo.get_by_id(admin.id)
    assert fetched.password_hash is None and fetched.activated_at is not None
    assert fetched.status is AccountStatus.AWAITING_PASSWORD


def test_a_deactivated_account_round_trips(repo, family_id):
    user = _family_user(family_id)
    user.deactivate()
    repo.save(user)

    assert repo.get_by_id(user.id).is_active is False


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

    assert repo.get_by_id(user.id).password_hash == "novo-hash"


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


@pytest.mark.parametrize("probe", ["' OR '1'='1", "joao' --", "%", "_", "joa%", "j_ao"])
def test_lookups_treat_wildcards_and_sql_as_plain_text(repo, family_id, probe):
    repo.save(_family_user(family_id, username="joao", email="joao@example.com"))

    assert repo.get_by_username(probe) is None
    assert repo.get_by_email(probe) is None


def test_exists_with_role(repo, family_id):
    assert repo.exists_with_role(Role.ROOT) is False

    repo.save(_family_user(family_id, role=Role.FAMILY_ADMIN))
    repo.save(_admin())
    assert repo.exists_with_role(Role.ROOT) is False
    assert repo.exists_with_role(Role.FAMILY_ADMIN) is True
    assert repo.exists_with_role(Role.SYSTEM_ADMIN) is True

    repo.save(User(role=Role.ROOT, username="root", email="root@example.com", password_hash="hash"))
    assert repo.exists_with_role(Role.ROOT) is True


def test_get_by_role(repo, family_id):
    assert repo.get_by_role(Role.ROOT) is None
    root = User(role=Role.ROOT, username="root", email="root@example.com", password_hash="hash")
    repo.save(root)
    repo.save(_admin())

    assert repo.get_by_role(Role.ROOT).id == root.id


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


def test_list_all_returns_users_of_every_level(repo, family_id):
    assert repo.list_all() == []

    repo.save(_admin())
    repo.save(_family_user(family_id))

    assert {u.username for u in repo.list_all()} == {"admin", "joao"}
