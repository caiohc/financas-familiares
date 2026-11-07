import uuid
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.identity.entities import Role
from infrastructure.database.models import FamilyModel, UserModel

_DEFAULT = object()
ACTIVATED = datetime(2026, 1, 1)


def _family(session: Session, name: str = "Família") -> str:
    model = FamilyModel(id=str(uuid.uuid4()), name=name)
    session.add(model)
    session.flush()
    return model.id


def _user(
    session: Session, username: str, email: str, family_id: str | None, role: Role | None = None, name=_DEFAULT,
    password_hash="hash", activated_at=_DEFAULT,
) -> UserModel:
    role = role or (Role.SYSTEM_ADMIN if family_id is None else Role.FAMILY_USER)
    if name is _DEFAULT:
        name = None if role is Role.ROOT else "Fulano"
    if activated_at is _DEFAULT:
        activated_at = ACTIVATED if password_hash is not None else None
    model = UserModel(
        id=str(uuid.uuid4()), role=role, family_id=family_id, name=name, username=username, email=email,
        password_hash=password_hash, activated_at=activated_at,
    )
    session.add(model)
    return model


def test_user_model_persists_with_family(session: Session):
    family_id = _family(session)
    user = _user(session, "joao", "joao@example.com", family_id)
    session.flush()

    fetched = session.get(UserModel, user.id)
    assert fetched.family_id == family_id
    assert fetched.username == "joao"
    assert fetched.email == "joao@example.com"
    assert fetched.role is Role.FAMILY_USER
    assert fetched.name == "Fulano"
    assert fetched.password_hash == "hash"
    assert fetched.activated_at == ACTIVATED


def test_a_new_user_is_active_by_default(session: Session):
    user = _user(session, "joao", "joao@example.com", _family(session))
    session.flush()
    assert session.get(UserModel, user.id).is_active is True


def test_user_model_has_no_must_change_password_column():
    assert not hasattr(UserModel, "must_change_password")


def test_admin_user_can_be_persisted_without_family(session: Session):
    admin = _user(session, "admin", "admin@example.com", None)
    session.flush()
    assert session.get(UserModel, admin.id).family_id is None


def test_duplicate_username_is_rejected(session: Session):
    family_id = _family(session)
    _user(session, "joao", "joao1@example.com", family_id)
    session.flush()
    _user(session, "joao", "joao2@example.com", family_id)
    with pytest.raises(IntegrityError):
        session.flush()


def test_duplicate_email_is_rejected(session: Session):
    family_id = _family(session)
    _user(session, "joao1", "joao@example.com", family_id)
    session.flush()
    _user(session, "joao2", "joao@example.com", family_id)
    with pytest.raises(IntegrityError):
        session.flush()


def test_username_uniqueness_is_case_insensitive(session: Session):
    family_id = _family(session)
    _user(session, "Joao", "a@example.com", family_id)
    session.flush()
    _user(session, "joao", "b@example.com", family_id)
    with pytest.raises(IntegrityError):
        session.flush()


def test_email_uniqueness_is_case_insensitive(session: Session):
    family_id = _family(session)
    _user(session, "a", "Joao@Example.com", family_id)
    session.flush()
    _user(session, "b", "joao@example.com", family_id)
    with pytest.raises(IntegrityError):
        session.flush()


def test_username_uniqueness_is_global_across_families(session: Session):
    _user(session, "joao", "a@example.com", _family(session, "Família A"))
    session.flush()
    _user(session, "joao", "b@example.com", _family(session, "Família B"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_email_uniqueness_is_global_including_admins(session: Session):
    _user(session, "admin", "x@example.com", None)
    session.flush()
    _user(session, "joao", "x@example.com", _family(session))
    with pytest.raises(IntegrityError):
        session.flush()


def test_username_and_email_are_independent_not_a_composite_key(session: Session):
    family_id = _family(session)
    _user(session, "joao", "a@example.com", family_id)
    _user(session, "maria", "b@example.com", family_id)
    session.flush()


# --- CHECK: família nula <=> ROOT ou SYSTEM_ADMIN ---

@pytest.mark.parametrize("role", [Role.ROOT, Role.SYSTEM_ADMIN])
def test_system_level_roles_with_family_are_rejected_by_the_database(session: Session, role):
    _user(session, "admin", "admin@example.com", _family(session), role=role)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("role", [Role.ROOT, Role.SYSTEM_ADMIN])
def test_system_level_roles_without_family_are_accepted(session: Session, role):
    _user(session, "admin", "admin@example.com", None, role=role)
    session.flush()


@pytest.mark.parametrize("role", [Role.FAMILY_ADMIN, Role.FAMILY_USER])
def test_family_roles_without_family_are_rejected_by_the_database(session: Session, role):
    _user(session, "joao", "joao@example.com", None, role=role)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("role", [Role.FAMILY_ADMIN, Role.FAMILY_USER])
def test_family_roles_with_family_are_accepted(session: Session, role):
    _user(session, "joao", "joao@example.com", _family(session), role=role)
    session.flush()


# --- CHECK: nome obrigatório para todos, exceto o ROOT ---

def test_root_without_name_is_accepted(session: Session):
    _user(session, "root", "root@example.com", None, role=Role.ROOT, name=None)
    session.flush()


@pytest.mark.parametrize("name", [None, "", "   "])
def test_system_admin_without_name_is_rejected_by_the_database(session: Session, name):
    _user(session, "admin", "admin@example.com", None, role=Role.SYSTEM_ADMIN, name=name)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("role", [Role.FAMILY_ADMIN, Role.FAMILY_USER])
@pytest.mark.parametrize("name", [None, "", "   "])
def test_family_roles_without_name_are_rejected_by_the_database(session: Session, role, name):
    _user(session, "joao", "joao@example.com", _family(session), role=role, name=name)
    with pytest.raises(IntegrityError):
        session.flush()


# --- CHECK: ciclo de vida da conta ---

def test_pending_account_without_password_nor_activation_is_accepted(session: Session):
    _user(session, "joao", "joao@example.com", _family(session), password_hash=None, activated_at=None)
    session.flush()


def test_account_awaiting_a_new_password_is_accepted(session: Session):
    _user(session, "admin", "admin@example.com", None, password_hash=None, activated_at=ACTIVATED)
    session.flush()


def test_a_password_without_activation_is_rejected_by_the_database(session: Session):
    _user(session, "joao", "joao@example.com", _family(session), password_hash="hash", activated_at=None)
    with pytest.raises(IntegrityError):
        session.flush()


def test_root_without_password_is_rejected_by_the_database(session: Session):
    _user(session, "root", "root@example.com", None, role=Role.ROOT, name=None, password_hash=None, activated_at=ACTIVATED)
    with pytest.raises(IntegrityError):
        session.flush()
