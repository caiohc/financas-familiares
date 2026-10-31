import uuid

import pytest

from domain.identity.entities import User
from domain.shared.exceptions import DomainValidationError


def test_user_creation_success():
    family_id = uuid.uuid4()
    user = User(family_id=family_id, username="joao", email="joao@example.com")
    assert user.family_id == family_id
    assert user.username == "joao"
    assert user.email == "joao@example.com"
    assert isinstance(user.id, uuid.UUID)


def test_admin_user_has_no_family():
    admin = User(username="admin", email="admin@example.com")
    assert admin.family_id is None


def test_user_has_no_member_id():
    assert not hasattr(User(username="joao", email="joao@example.com"), "member_id")


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_user_missing_username(blank):
    with pytest.raises(DomainValidationError, match="Nome de usuário é obrigatório"):
        User(family_id=uuid.uuid4(), username=blank, email="joao@example.com")


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_user_missing_email(blank):
    with pytest.raises(DomainValidationError, match="E-mail é obrigatório"):
        User(family_id=uuid.uuid4(), username="joao", email=blank)


def test_user_username_and_email_are_stripped():
    user = User(username="  joao  ", email="  joao@example.com  ")
    assert user.username == "joao"
    assert user.email == "joao@example.com"
