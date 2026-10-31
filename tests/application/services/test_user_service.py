import uuid

import pytest

from application.dtos.identity_dtos import CreateRootDTO
from application.services.user_service import UserService
from domain.identity.entities import Role, User
from domain.shared.exceptions import DomainValidationError, EntityAlreadyExistsError
from fakes.family_fakes import FakeUnitOfWork
from fakes.identity_fakes import FakePasswordHasher


@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def service(uow):
    return UserService(uow, FakePasswordHasher())


def _dto(**overrides) -> CreateRootDTO:
    data = dict(username="root", email="root@example.com", temporary_password="senha-temporaria")
    data.update(overrides)
    return CreateRootDTO(**data)


def _family_user(**overrides) -> User:
    data = dict(
        role=Role.FAMILY_USER, family_id=uuid.uuid4(), name="Maria", username="maria", email="maria@example.com",
        password_hash="h",
    )
    data.update(overrides)
    return User(**data)


def test_create_root(service: UserService, uow: FakeUnitOfWork):
    response = service.create_root(_dto())

    assert response.role is Role.ROOT
    assert response.family_id is None
    assert response.name is None
    assert (response.username, response.email) == ("root", "root@example.com")
    assert response.must_change_password is True
    assert uow.users.get_by_id(response.id) is not None
    assert uow.committed is True


def test_password_is_stored_hashed_never_in_plain_text(service: UserService, uow: FakeUnitOfWork):
    response = service.create_root(_dto(temporary_password="senha-temporaria"))

    stored = uow.users.get_by_id(response.id)
    assert stored.password_hash == FakePasswordHasher().hash("senha-temporaria")
    assert stored.password_hash != "senha-temporaria"
    assert not hasattr(response, "password_hash")


def test_username_and_email_are_stripped(service: UserService):
    response = service.create_root(_dto(username="  root  ", email="  root@example.com "))
    assert (response.username, response.email) == ("root", "root@example.com")


def test_refuses_when_a_root_already_exists(service: UserService, uow: FakeUnitOfWork):
    uow.users.save(User(role=Role.ROOT, username="antigo", email="antigo@example.com", password_hash="h"))

    with pytest.raises(EntityAlreadyExistsError, match="usuário root") as exc:
        service.create_root(_dto())

    assert exc.value.field == "role"
    assert len(uow.users.users) == 1
    assert uow.committed is False


@pytest.mark.parametrize("other", [
    User(role=Role.SYSTEM_ADMIN, name="Caio", username="caio", email="caio@example.com", password_hash="h"),
    User(role=Role.FAMILY_ADMIN, family_id=uuid.uuid4(), name="Ana", username="ana", email="ana@example.com",
         password_hash="h"),
])
def test_other_users_do_not_block_the_root(service: UserService, uow: FakeUnitOfWork, other):
    uow.users.save(other)

    assert service.create_root(_dto()).role is Role.ROOT


def test_duplicate_username_ignoring_case_raises(service: UserService, uow: FakeUnitOfWork):
    uow.users.save(_family_user(username="Root", email="outro@example.com"))

    with pytest.raises(EntityAlreadyExistsError) as exc:
        service.create_root(_dto(username="root"))

    assert exc.value.field == "username"
    assert uow.committed is False


def test_duplicate_email_ignoring_case_raises(service: UserService, uow: FakeUnitOfWork):
    uow.users.save(_family_user(username="outro", email="ROOT@example.com"))

    with pytest.raises(EntityAlreadyExistsError) as exc:
        service.create_root(_dto())

    assert exc.value.field == "email"
    assert uow.committed is False


@pytest.mark.parametrize("overrides, message", [
    ({"username": "  "}, "Nome de usuário é obrigatório"),
    ({"email": ""}, "E-mail é obrigatório"),
    ({"temporary_password": ""}, "Senha é obrigatória"),
    ({"temporary_password": "curta"}, "pelo menos 8 caracteres"),
])
def test_invalid_input_raises_and_saves_nothing(service: UserService, uow: FakeUnitOfWork, overrides, message):
    with pytest.raises(DomainValidationError, match=message):
        service.create_root(_dto(**overrides))

    assert uow.users.users == {}
    assert uow.committed is False
