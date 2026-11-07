import uuid

import pytest

from domain.identity.entities import MIN_PASSWORD_LENGTH, Role, User
from domain.shared.exceptions import DomainValidationError


def _user(**overrides) -> User:
    data = dict(
        role=Role.FAMILY_USER, family_id=uuid.uuid4(), name="João", username="joao", email="joao@example.com",
        password_hash="hash",
    )
    data.update(overrides)
    return User(**data)


def _root(**overrides) -> User:
    data = dict(role=Role.ROOT, family_id=None, name=None)
    data.update(overrides)
    return _user(**data)


def test_user_creation_success():
    family_id = uuid.uuid4()
    user = _user(family_id=family_id)
    assert user.role is Role.FAMILY_USER
    assert user.family_id == family_id
    assert user.name == "João"
    assert user.username == "joao"
    assert user.email == "joao@example.com"
    assert user.password_hash == "hash"
    assert isinstance(user.id, uuid.UUID)


def test_new_user_must_change_password_by_default():
    assert _user().must_change_password is True


def test_user_has_no_member_id():
    assert not hasattr(_user(), "member_id")


# --- Papel e família (invariante: family_id é None <=> ROOT ou SYSTEM_ADMIN) ---

def test_root_has_no_family():
    root = _root()
    assert root.family_id is None
    assert (root.is_root, root.is_system_admin, root.is_family_admin) == (True, False, False)


def test_system_admin_has_no_family():
    admin = _user(role=Role.SYSTEM_ADMIN, family_id=None)
    assert admin.family_id is None
    assert (admin.is_root, admin.is_system_admin, admin.is_family_admin) == (False, True, False)


@pytest.mark.parametrize("role", [Role.ROOT, Role.SYSTEM_ADMIN])
def test_system_level_roles_with_family_are_rejected(role):
    with pytest.raises(DomainValidationError, match="não pode pertencer a uma família") as exc:
        _user(role=role, family_id=uuid.uuid4())
    assert exc.value.field == "family_id"


@pytest.mark.parametrize("role", [Role.FAMILY_ADMIN, Role.FAMILY_USER])
def test_family_roles_require_a_family(role):
    with pytest.raises(DomainValidationError, match="deve pertencer a uma família") as exc:
        _user(role=role, family_id=None)
    assert exc.value.field == "family_id"


def test_family_admin_flags():
    admin = _user(role=Role.FAMILY_ADMIN)
    assert (admin.is_root, admin.is_system_admin, admin.is_family_admin) == (False, False, True)


@pytest.mark.parametrize("invalid", [None, "SYSTEM_ADMIN", "", 1])
def test_role_must_be_a_role_enum(invalid):
    with pytest.raises(DomainValidationError, match="Papel do usuário é obrigatório") as exc:
        _user(role=invalid, family_id=None)
    assert exc.value.field == "role"


# --- Nome da pessoa (obrigatório para todos, exceto o ROOT) ---

@pytest.mark.parametrize("role, family_id", [
    (Role.SYSTEM_ADMIN, None),
    (Role.FAMILY_ADMIN, uuid.uuid4()),
    (Role.FAMILY_USER, uuid.uuid4()),
])
@pytest.mark.parametrize("blank", [None, "", "   "])
def test_name_is_required_for_everyone_but_root(role, family_id, blank):
    with pytest.raises(DomainValidationError, match="Nome é obrigatório") as exc:
        _user(role=role, family_id=family_id, name=blank)
    assert exc.value.field == "name"


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_root_may_have_no_name(blank):
    assert _root(name=blank).name is None


def test_root_may_have_a_name():
    assert _root(name="  Administrador  ").name == "Administrador"


def test_name_is_stripped():
    assert _user(name="  João Silva  ").name == "João Silva"


# --- Campos obrigatórios ---

@pytest.mark.parametrize("blank", [None, "", "   "])
def test_user_missing_username(blank):
    with pytest.raises(DomainValidationError, match="Nome de usuário é obrigatório"):
        _user(username=blank)


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_user_missing_email(blank):
    with pytest.raises(DomainValidationError, match="E-mail é obrigatório"):
        _user(email=blank)


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_user_missing_password_hash(blank):
    with pytest.raises(DomainValidationError, match="Senha é obrigatória") as exc:
        _user(password_hash=blank)
    assert exc.value.field == "password"


def test_user_username_and_email_are_stripped():
    user = _user(username="  joao  ", email="  joao@example.com  ")
    assert user.username == "joao"
    assert user.email == "joao@example.com"


# --- Política de senha (aplicada à senha em texto, antes do hash) ---

def test_raw_password_valid():
    assert User.validate_raw_password("x" * MIN_PASSWORD_LENGTH) == "x" * MIN_PASSWORD_LENGTH


def test_raw_password_is_not_stripped():
    assert User.validate_raw_password("  senha longa  ") == "  senha longa  "


@pytest.mark.parametrize("blank", [None, "", "        "])
def test_raw_password_required(blank):
    with pytest.raises(DomainValidationError, match="Senha é obrigatória"):
        User.validate_raw_password(blank)


def test_raw_password_too_short():
    with pytest.raises(DomainValidationError, match=f"pelo menos {MIN_PASSWORD_LENGTH} caracteres"):
        User.validate_raw_password("x" * (MIN_PASSWORD_LENGTH - 1))


# --- Troca de senha ---

def test_set_temporary_password_forces_change():
    user = _user(must_change_password=False)
    user.set_temporary_password("novo-hash")
    assert (user.password_hash, user.must_change_password) == ("novo-hash", True)


def test_change_password_clears_forced_change():
    user = _user(must_change_password=True)
    user.change_password("novo-hash")
    assert (user.password_hash, user.must_change_password) == ("novo-hash", False)


@pytest.mark.parametrize("method", ["set_temporary_password", "change_password"])
def test_password_change_rejects_blank_hash_and_keeps_state(method):
    user = _user(must_change_password=False)
    with pytest.raises(DomainValidationError):
        getattr(user, method)("  ")
    assert (user.password_hash, user.must_change_password) == ("hash", False)


# --- Confirmação da senha ---

def test_password_confirmation_accepts_identical_passwords():
    User.validate_password_confirmation("senha-temporaria", "senha-temporaria")


@pytest.mark.parametrize("confirmation", ["Senha-Temporaria", "senha-temporaria ", "", None])
def test_password_confirmation_rejects_any_difference(confirmation):
    with pytest.raises(DomainValidationError, match="senhas informadas não conferem") as exc:
        User.validate_password_confirmation("senha-temporaria", confirmation)
    assert exc.value.field == "password_confirmation"
