"""Usuário root: criação e redefinição de senha pela CLI (sem ator: quem executa tem acesso ao servidor)."""
import pytest

from application.dtos.identity_dtos import CreateRootDTO
from domain.identity.entities import AccountStatus, Role
from domain.shared.exceptions import DomainValidationError, EntityAlreadyExistsError, EntityNotFoundError
from fakes.identity_builders import make_user
from fakes.identity_fakes import FakePasswordHasher


def _dto(**overrides) -> CreateRootDTO:
    data = dict(
        username="root", email="root@example.com", password="senha-do-root-123",
        password_confirmation="senha-do-root-123",
    )
    data.update(overrides)
    return CreateRootDTO(**data)


def test_create_root(user_service, uow):
    response = user_service.create_root(_dto())

    assert response.role is Role.ROOT
    assert response.family_id is None
    assert response.name is None
    assert (response.username, response.email) == ("root", "root@example.com")
    assert response.status is AccountStatus.ACTIVE
    assert uow.users.get_by_id(response.id) is not None
    assert uow.committed is True


def test_root_is_created_activated_with_the_password_chosen_at_the_terminal(user_service, uow):
    response = user_service.create_root(_dto())

    stored = uow.users.get_by_id(response.id)
    assert stored.password_hash == FakePasswordHasher().hash("senha-do-root-123")
    assert stored.activated_at is not None
    assert stored.can_authenticate is True


def test_password_is_stored_hashed_never_in_plain_text(user_service, uow):
    response = user_service.create_root(_dto())

    stored = uow.users.get_by_id(response.id)
    assert stored.password_hash != "senha-do-root-123"
    assert not hasattr(response, "password_hash")


def test_username_and_email_are_stripped(user_service):
    response = user_service.create_root(_dto(username="  root  ", email="  root@example.com "))
    assert (response.username, response.email) == ("root", "root@example.com")


def test_refuses_when_a_root_already_exists(user_service, uow):
    make_user(uow, Role.ROOT, username="antigo")

    with pytest.raises(EntityAlreadyExistsError, match="usuário root") as exc:
        user_service.create_root(_dto())

    assert exc.value.field == "role"
    assert len(uow.users.users) == 1
    assert uow.committed is False


@pytest.mark.parametrize("other_role", [Role.SYSTEM_ADMIN, Role.FAMILY_ADMIN])
def test_other_users_do_not_block_the_root(user_service, uow, other_role):
    make_user(uow, other_role)

    assert user_service.create_root(_dto()).role is Role.ROOT


def test_duplicate_username_ignoring_case_raises(user_service, uow):
    make_user(uow, Role.FAMILY_USER, username="Root", email="outro@example.com")

    with pytest.raises(EntityAlreadyExistsError) as exc:
        user_service.create_root(_dto(username="root"))

    assert exc.value.field == "username"
    assert uow.committed is False


def test_duplicate_email_ignoring_case_raises(user_service, uow):
    make_user(uow, Role.FAMILY_USER, username="outro", email="ROOT@example.com")

    with pytest.raises(EntityAlreadyExistsError) as exc:
        user_service.create_root(_dto())

    assert exc.value.field == "email"
    assert uow.committed is False


@pytest.mark.parametrize("overrides, message", [
    ({"username": "  "}, "Nome de usuário é obrigatório"),
    ({"email": ""}, "E-mail é obrigatório"),
    ({"email": "nao-e-email"}, "e-mail válido"),
    ({"password": "", "password_confirmation": ""}, "Senha é obrigatória"),
    ({"password": "curta", "password_confirmation": "curta"}, "pelo menos 8 caracteres"),
    ({"password_confirmation": "outra-senha-123"}, "senhas informadas não conferem"),
    ({"password_confirmation": None}, "senhas informadas não conferem"),
])
def test_invalid_input_raises_and_saves_nothing(user_service, uow, overrides, message):
    with pytest.raises(DomainValidationError, match=message):
        user_service.create_root(_dto(**overrides))

    assert uow.users.users == {}
    assert uow.committed is False


# --- Redefinição da senha do root (CLI) ---

def test_reset_root_password_replaces_the_hash(user_service, uow):
    root = make_user(uow, Role.ROOT, username="root", password="senha-antiga-123")
    old_hash = root.password_hash

    response = user_service.reset_root_password("senha-nova-1234", "senha-nova-1234")

    stored = uow.users.get_by_id(root.id)
    assert stored.password_hash == FakePasswordHasher().hash("senha-nova-1234") != old_hash
    assert response.status is AccountStatus.ACTIVE
    assert uow.committed is True


def test_reset_root_password_without_a_root_fails(user_service):
    with pytest.raises(EntityNotFoundError, match="create-root"):
        user_service.reset_root_password("senha-nova-1234", "senha-nova-1234")


@pytest.mark.parametrize("password, confirmation, message", [
    ("curta", "curta", "pelo menos 8 caracteres"),
    ("senha-nova-1234", "senha-diferente-12", "não conferem"),
    ("senha-nova-1234", None, "não conferem"),
    ("", "", "Senha é obrigatória"),
])
def test_reset_root_password_rejects_invalid_input_and_keeps_the_old_one(user_service, uow, password, confirmation, message):
    root = make_user(uow, Role.ROOT, username="root", password="senha-antiga-123")
    old_hash = root.password_hash

    with pytest.raises(DomainValidationError, match=message):
        user_service.reset_root_password(password, confirmation)

    assert uow.users.get_by_id(root.id).password_hash == old_hash
    assert uow.committed is False


def test_reset_root_password_does_not_touch_other_users(user_service, uow):
    make_user(uow, Role.ROOT, username="root")
    admin = make_user(uow, Role.SYSTEM_ADMIN, username="admin", password="senha-do-admin-1")
    old_hash = admin.password_hash

    user_service.reset_root_password("senha-nova-1234", "senha-nova-1234")

    assert uow.users.get_by_id(admin.id).password_hash == old_hash


# --- Consultas da CLI e mensagens claras ---

def test_get_root_is_none_until_the_root_exists(user_service, uow):
    assert user_service.get_root() is None

    user_service.create_root(_dto())

    root = user_service.get_root()
    assert (root.username, root.email, root.role) == ("root", "root@example.com", Role.ROOT)


def test_get_root_ignores_other_accounts(user_service, uow):
    make_user(uow, Role.SYSTEM_ADMIN)
    assert user_service.get_root() is None


def test_the_second_root_message_names_the_existing_one(user_service, uow):
    make_user(uow, Role.ROOT, username="primeiro")

    with pytest.raises(EntityAlreadyExistsError) as exc:
        user_service.create_root(_dto())

    message = str(exc.value)
    assert 'Já existe um usuário root.' in message and "um segundo não pode ser criado" in message


def test_check_root_username_returns_the_normalized_name_when_free(user_service):
    assert user_service.check_root_username("  root  ") == "root"


@pytest.mark.parametrize("taken", ["pessoa", "PESSOA", "  Pessoa "])
def test_check_root_username_refuses_a_name_in_use_ignoring_case(user_service, uow, taken):
    make_user(uow, username="pessoa")

    with pytest.raises(EntityAlreadyExistsError, match='já está cadastrado no sistema') as exc:
        user_service.check_root_username(taken)

    assert exc.value.field == "username"


@pytest.mark.parametrize("blank", [None, "", "  "])
def test_check_root_username_requires_a_value(user_service, blank):
    with pytest.raises(DomainValidationError, match="Nome de usuário é obrigatório"):
        user_service.check_root_username(blank)


def test_check_root_email_returns_the_normalized_address_when_free(user_service):
    assert user_service.check_root_email("  Root@Example.COM ") == "Root@example.com"


def test_check_root_email_names_the_account_that_owns_it(user_service, uow):
    make_user(uow, username="caiohc", email="caio@example.com")

    with pytest.raises(EntityAlreadyExistsError) as exc:
        user_service.check_root_email("CAIO@example.com")

    assert 'já está cadastrado no sistema' in str(exc.value) and exc.value.field == "email"


def test_check_root_email_allows_the_roots_own_address_when_asked_to_ignore_it(user_service, uow):
    root = make_user(uow, Role.ROOT, username="root", email="root@example.com")

    assert user_service.check_root_email("root@example.com", ignore_user_id=root.id) == "root@example.com"
    with pytest.raises(EntityAlreadyExistsError):
        user_service.check_root_email("root@example.com")


@pytest.mark.parametrize("bad", ["", "nao-e-email", "a@b"])
def test_check_root_email_rejects_invalid_addresses(user_service, bad):
    with pytest.raises(DomainValidationError):
        user_service.check_root_email(bad)


def test_create_root_reports_an_email_in_use_by_naming_the_owner(user_service, uow):
    make_user(uow, username="caiohc", email="root@example.com")

    with pytest.raises(EntityAlreadyExistsError, match='já está cadastrado no sistema'):
        user_service.create_root(_dto())

    assert uow.users.get_by_role(Role.ROOT) is None


# --- Troca do e-mail do root (CLI) ---

def _root_with(uow, **overrides):
    return make_user(uow, Role.ROOT, username="root", email="root@example.com", **overrides)


def test_change_root_email(user_service, uow):
    root = _root_with(uow)

    response = user_service.change_root_email("novo@example.com", "novo@example.com")

    assert response.email == "novo@example.com"
    assert uow.users.get_by_id(root.id).email == "novo@example.com"
    assert uow.committed is True


def test_change_root_email_normalizes_and_ignores_case_in_the_confirmation(user_service, uow):
    _root_with(uow)

    response = user_service.change_root_email("  Novo@Example.COM ", " novo@example.com")

    assert response.email == "Novo@example.com"


def test_change_root_email_keeps_password_activation_and_status(user_service, uow):
    root = _root_with(uow)
    before = (root.password_hash, root.activated_at, root.is_active, root.username)

    user_service.change_root_email("novo@example.com", "novo@example.com")

    stored = uow.users.get_by_id(root.id)
    assert (stored.password_hash, stored.activated_at, stored.is_active, stored.username) == before


def test_change_root_email_works_even_though_the_root_is_activated(user_service, uow):
    root = _root_with(uow)
    assert root.activated_at is not None

    user_service.change_root_email("novo@example.com", "novo@example.com")


@pytest.mark.parametrize("confirmation", ["outro@example.com", "", None])
def test_change_root_email_requires_the_confirmation_to_match(user_service, uow, confirmation):
    root = _root_with(uow)

    with pytest.raises(DomainValidationError, match="e-mails informados não conferem"):
        user_service.change_root_email("novo@example.com", confirmation)

    assert uow.users.get_by_id(root.id).email == "root@example.com" and uow.committed is False


@pytest.mark.parametrize("same", ["root@example.com", "ROOT@example.com", "  root@Example.COM "])
def test_change_root_email_refuses_the_current_address(user_service, uow, same):
    _root_with(uow)

    with pytest.raises(DomainValidationError, match="igual ao atual"):
        user_service.change_root_email(same, same)


def test_change_root_email_refuses_an_address_of_another_account_and_names_it(user_service, uow):
    root = _root_with(uow)
    make_user(uow, username="caiohc", email="caio@example.com")

    with pytest.raises(EntityAlreadyExistsError, match='já está cadastrado no sistema'):
        user_service.change_root_email("CAIO@example.com", "caio@example.com")

    assert uow.users.get_by_id(root.id).email == "root@example.com" and uow.committed is False


@pytest.mark.parametrize("bad", ["", None, "nao-e-email", "a@b"])
def test_change_root_email_rejects_invalid_addresses(user_service, uow, bad):
    root = _root_with(uow)

    with pytest.raises(DomainValidationError):
        user_service.change_root_email(bad, bad)

    assert uow.users.get_by_id(root.id).email == "root@example.com"


def test_change_root_email_without_a_root_says_how_to_create_one(user_service):
    with pytest.raises(EntityNotFoundError, match="create-root"):
        user_service.change_root_email("novo@example.com", "novo@example.com")


def test_change_root_email_does_not_touch_other_accounts(user_service, uow):
    _root_with(uow)
    other = make_user(uow, Role.SYSTEM_ADMIN, username="admin", email="admin@example.com")

    user_service.change_root_email("novo@example.com", "novo@example.com")

    assert uow.users.get_by_id(other.id).email == "admin@example.com"
