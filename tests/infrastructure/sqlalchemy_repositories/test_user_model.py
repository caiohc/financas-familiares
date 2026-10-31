import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from infrastructure.database.models import FamilyModel, UserModel


def _family(session: Session, name: str = "Família") -> str:
    model = FamilyModel(id=str(uuid.uuid4()), name=name)
    session.add(model)
    session.flush()
    return model.id


def _user(session: Session, username: str, email: str, family_id: str | None) -> UserModel:
    model = UserModel(id=str(uuid.uuid4()), family_id=family_id, username=username, email=email)
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
