import uuid

import pytest

from domain.identity.entities import Role, User
from domain.shared.exceptions import DomainValidationError


def _user(**overrides) -> User:
    data = dict(
        role=Role.FAMILY_USER, family_id=uuid.uuid4(), name="João", username="joao", email="joao@example.com",
        password_hash="hash",
    )
    data.update(overrides)
    return User(**data)


def test_update_profile_changes_name_username_and_email():
    user = _user()
    user.update_profile("  Maria  ", "  maria  ", "  maria@example.com ")
    assert (user.name, user.username, user.email) == ("Maria", "maria", "maria@example.com")


def test_update_profile_does_not_touch_role_family_or_password():
    user = _user(must_change_password=False)
    family_id, user_id = user.family_id, user.id

    user.update_profile("Maria", "maria", "maria@example.com")

    assert (user.role, user.family_id, user.id) == (Role.FAMILY_USER, family_id, user_id)
    assert (user.password_hash, user.must_change_password) == ("hash", False)


@pytest.mark.parametrize("name, username, email, message", [
    ("  ", "maria", "maria@example.com", "Nome é obrigatório"),
    (None, "maria", "maria@example.com", "Nome é obrigatório"),
    ("Maria", "  ", "maria@example.com", "Nome de usuário é obrigatório"),
    ("Maria", "maria", "", "E-mail é obrigatório"),
])
def test_update_profile_rejects_invalid_values_and_keeps_the_entity_untouched(name, username, email, message):
    user = _user()

    with pytest.raises(DomainValidationError, match=message):
        user.update_profile(name, username, email)

    assert (user.name, user.username, user.email) == ("João", "joao", "joao@example.com")


def test_root_profile_may_be_updated_without_name():
    root = _user(role=Role.ROOT, family_id=None, name="Antigo")

    root.update_profile(None, "root2", "root2@example.com")

    assert (root.name, root.username) == (None, "root2")
