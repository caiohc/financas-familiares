import uuid
from datetime import datetime

import pytest

from domain.identity.entities import AccountStatus, MIN_PASSWORD_LENGTH, Role, User
from domain.shared.exceptions import DomainValidationError


def _user(**overrides) -> User:
    data = dict(
        role=Role.FAMILY_USER, family_id=uuid.uuid4(), name="João", username="joao", email="joao@example.com",
    )
    data.update(overrides)
    return User(**data)


def _root(**overrides) -> User:
    data = dict(role=Role.ROOT, family_id=None, name=None, password_hash="hash")
    data.update(overrides)
    return _user(**data)


def _active(**overrides) -> User:
    return _user(password_hash="hash", **overrides)


def test_user_creation_success():
    family_id = uuid.uuid4()
    user = _user(family_id=family_id)
    assert user.role is Role.FAMILY_USER
    assert user.family_id == family_id
    assert user.name == "João"
    assert user.username == "joao"
    assert user.email == "joao@example.com"
    assert isinstance(user.id, uuid.UUID)


def test_user_has_no_member_id():
    assert not hasattr(_user(), "member_id")


def test_user_has_no_temporary_password_concept():
    assert not hasattr(_user(), "must_change_password")
    assert not hasattr(_user(), "set_temporary_password")


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
        _user(role=role, family_id=uuid.uuid4(), password_hash="hash")
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


def test_user_username_is_stripped():
    assert _user(username="  joao  ").username == "joao"


# --- E-mail: formato e normalização ---

@pytest.mark.parametrize("invalid", [
    "sem-arroba", "a@b", "@example.com", "joao@", "joao@@example.com", "jo ao@example.com",
    "joao@exa mple.com", "joao@localhost", "joao@example..com", "<script>@example.com",
])
def test_user_with_invalid_email_is_rejected(invalid):
    with pytest.raises(DomainValidationError, match="e-mail válido") as exc:
        _user(email=invalid)
    assert exc.value.field == "email"


def test_email_is_stripped_and_its_domain_lowercased():
    assert _user(email="  Joao@Example.COM  ").email == "Joao@example.com"


def test_email_with_plus_tag_is_kept_as_typed():
    assert _user(email="joao+loja@example.com").email == "joao+loja@example.com"


def test_validate_email_confirmation_accepts_equal_ignoring_case_and_edges():
    User.validate_email_confirmation("joao@example.com", "  JOAO@Example.com ")


@pytest.mark.parametrize("confirmation", ["joao@example.org", "", None, "joao@example.co"])
def test_validate_email_confirmation_rejects_differences(confirmation):
    with pytest.raises(DomainValidationError, match="e-mails informados não conferem") as exc:
        User.validate_email_confirmation("joao@example.com", confirmation)
    assert exc.value.field == "email_confirmation"


# --- Situação da conta ---

def test_new_user_without_password_is_pending_and_cannot_authenticate():
    user = _user()
    assert user.status is AccountStatus.PENDING
    assert (user.is_pending, user.has_password, user.can_authenticate) == (True, False, False)
    assert user.activated_at is None


def test_user_with_password_is_active_and_activated():
    user = _active()
    assert user.status is AccountStatus.ACTIVE
    assert (user.is_pending, user.has_password, user.can_authenticate) == (False, True, True)
    assert isinstance(user.activated_at, datetime)


def test_explicit_activation_date_is_kept():
    when = datetime(2026, 1, 2, 3, 4, 5)
    assert _active(activated_at=when).activated_at == when


def test_deactivated_user_cannot_authenticate_whatever_the_stage():
    assert _active(is_active=False).status is AccountStatus.DEACTIVATED
    assert _active(is_active=False).can_authenticate is False
    assert _user(is_active=False).status is AccountStatus.DEACTIVATED


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_password_hash_is_not_a_pending_account(blank):
    with pytest.raises(DomainValidationError, match="Senha é obrigatória"):
        _user(password_hash=blank)


def test_root_always_has_a_password():
    with pytest.raises(DomainValidationError, match="root precisa ter senha"):
        _user(role=Role.ROOT, family_id=None, name=None)


# --- Definição e troca de senha ---

def test_define_password_activates_a_pending_account():
    user = _user()
    when = datetime(2026, 5, 6, 7, 8, 9)

    user.define_password("novo-hash", when)

    assert (user.password_hash, user.activated_at, user.status) == ("novo-hash", when, AccountStatus.ACTIVE)


def test_define_password_keeps_the_original_activation_date():
    first = datetime(2026, 1, 1)
    user = _active(role=Role.SYSTEM_ADMIN, family_id=None, activated_at=first)
    user.revoke_password()

    user.define_password("outro-hash", datetime(2026, 9, 9))

    assert user.activated_at == first


@pytest.mark.parametrize("blank", [None, "", "  "])
def test_define_password_rejects_a_blank_hash(blank):
    user = _user()
    with pytest.raises(DomainValidationError):
        user.define_password(blank)
    assert user.has_password is False


def test_change_password_replaces_the_hash_and_keeps_activation():
    user = _active()
    activated = user.activated_at
    user.change_password("novo-hash")
    assert (user.password_hash, user.activated_at) == ("novo-hash", activated)


@pytest.mark.parametrize("blank", [None, "", "  "])
def test_change_password_rejects_a_blank_hash_and_keeps_state(blank):
    user = _active()
    with pytest.raises(DomainValidationError):
        user.change_password(blank)
    assert user.password_hash == "hash"


def test_revoke_password_leaves_an_activated_account_awaiting_a_new_password():
    user = _active(role=Role.SYSTEM_ADMIN, family_id=None)

    user.revoke_password()

    assert user.status is AccountStatus.AWAITING_PASSWORD
    assert (user.is_pending, user.can_authenticate) == (False, False)
    assert user.activated_at is not None


def test_root_password_cannot_be_revoked():
    root = _root()
    with pytest.raises(DomainValidationError, match="root precisa ter senha"):
        root.revoke_password()
    assert root.password_hash == "hash"


# --- Desativar e reativar ---

def test_deactivate_and_reactivate():
    user = _active()
    user.deactivate()
    assert (user.is_active, user.status) == (False, AccountStatus.DEACTIVATED)
    user.reactivate()
    assert (user.is_active, user.status) == (True, AccountStatus.ACTIVE)


def test_root_cannot_be_deactivated():
    root = _root()
    with pytest.raises(DomainValidationError, match="root não pode ser desativado"):
        root.deactivate()
    assert root.is_active is True


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


def test_password_confirmation_accepts_identical_passwords():
    User.validate_password_confirmation("senha-segura-123", "senha-segura-123")


@pytest.mark.parametrize("confirmation", ["Senha-Segura-123", "senha-segura-123 ", " senha-segura-123", "", None])
def test_password_confirmation_rejects_any_difference(confirmation):
    with pytest.raises(DomainValidationError, match="senhas informadas não conferem") as exc:
        User.validate_password_confirmation("senha-segura-123", confirmation)
    assert exc.value.field == "password_confirmation"


# --- Edição administrativa dos dados de identificação ---

def test_update_profile_changes_name_username_and_email_of_a_pending_account():
    user = _user()
    user.update_profile("  Maria  ", "  maria  ", "  maria@example.com ")
    assert (user.name, user.username, user.email) == ("Maria", "maria", "maria@example.com")


def test_update_profile_does_not_touch_role_family_or_password():
    user = _active()
    family_id, user_id, hashed = user.family_id, user.id, user.password_hash

    user.update_profile("Maria", "maria", "joao@example.com")

    assert (user.role, user.family_id, user.id, user.password_hash) == (Role.FAMILY_USER, family_id, user_id, hashed)


@pytest.mark.parametrize("name, username, email, message", [
    ("  ", "maria", "maria@example.com", "Nome é obrigatório"),
    (None, "maria", "maria@example.com", "Nome é obrigatório"),
    ("Maria", "  ", "maria@example.com", "Nome de usuário é obrigatório"),
    ("Maria", "maria", "", "E-mail é obrigatório"),
    ("Maria", "maria", "invalido", "e-mail válido"),
])
def test_update_profile_rejects_invalid_values_and_keeps_the_entity_untouched(name, username, email, message):
    user = _user()

    with pytest.raises(DomainValidationError, match=message):
        user.update_profile(name, username, email)

    assert (user.name, user.username, user.email) == ("João", "joao", "joao@example.com")


def test_update_profile_cannot_change_the_email_after_activation():
    user = _active()

    with pytest.raises(DomainValidationError, match="não pode ser alterado depois que a conta foi ativada") as exc:
        user.update_profile("João", "joao", "outro@example.com")

    assert exc.value.field == "email"
    assert user.email == "joao@example.com"


def test_update_profile_after_activation_still_changes_name_and_username():
    user = _active()
    user.update_profile("João Silva", "joao.silva", "JOAO@example.com")   # mesmo e-mail, só a caixa muda
    assert (user.name, user.username) == ("João Silva", "joao.silva")


def test_awaiting_password_account_keeps_the_email_locked():
    user = _active(role=Role.SYSTEM_ADMIN, family_id=None)
    user.revoke_password()
    with pytest.raises(DomainValidationError, match="depois que a conta foi ativada"):
        user.update_profile("João", "joao", "outro@example.com")


def test_root_profile_may_be_updated_without_name_and_keeps_its_email():
    root = _root(name="Antigo")

    root.update_profile(None, "root2", root.email)

    assert (root.name, root.username) == (None, "root2")


# --- Troca de e-mail por quem tem o direito (o próprio usuário / a CLI do root) ---

def test_change_email_replaces_and_normalizes_the_address():
    user = _active()
    user.change_email("  Novo@Example.COM ")
    assert user.email == "Novo@example.com"


def test_change_email_works_after_activation_unlike_the_administrative_edit():
    user = _active()
    with pytest.raises(DomainValidationError, match="depois que a conta foi ativada"):
        user.update_profile(user.name, user.username, "outro@example.com")

    user.change_email("outro@example.com")

    assert user.email == "outro@example.com"


@pytest.mark.parametrize("bad", [None, "", "   ", "sem-arroba", "a@b", "joao@@example.com"])
def test_change_email_rejects_invalid_values_and_keeps_the_current_one(bad):
    user = _active()
    with pytest.raises(DomainValidationError):
        user.change_email(bad)
    assert user.email == "joao@example.com"


def test_change_email_keeps_everything_else():
    root = _root()
    before = (root.username, root.password_hash, root.role, root.activated_at, root.is_active)

    root.change_email("root.novo@example.com")

    assert (root.username, root.password_hash, root.role, root.activated_at, root.is_active) == before
