"""CRUD de usuário cadastrado por um administrador (o usuário root é coberto em test_user_service.py)."""
import uuid

import pytest

from application.dtos.identity_dtos import CreateUserDTO, UpdateUserDTO
from application.services.user_service import UserService
from domain.family.entities import Family
from domain.identity.entities import Role, User
from domain.identity.exceptions import user_has_dependencies
from domain.shared.exceptions import (
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)
from fakes.family_fakes import FakeUnitOfWork
from fakes.identity_fakes import FakePasswordHasher


@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def service(uow):
    return UserService(uow, FakePasswordHasher())


@pytest.fixture
def family(uow):
    family = Family(name="Silva")
    uow.families.save(family)
    return family


def _create_dto(**overrides) -> CreateUserDTO:
    data = dict(
        role=Role.SYSTEM_ADMIN, family_id=None, name="Caio", username="caio", email="caio@example.com",
        temporary_password="senha-temporaria",
    )
    data.update(overrides)
    return CreateUserDTO(**data)


def _saved(uow, **overrides) -> User:
    data = dict(
        role=Role.FAMILY_USER, family_id=uuid.uuid4(), name="Maria", username="maria", email="maria@example.com",
        password_hash="h",
    )
    data.update(overrides)
    user = User(**data)
    uow.users.save(user)
    return user


def _saved_root(uow) -> User:
    return _saved(uow, role=Role.ROOT, family_id=None, name=None, username="root", email="root@example.com")


# --- Criação ---

def test_create_system_admin(service: UserService, uow: FakeUnitOfWork):
    response = service.create_user(_create_dto())

    assert (response.role, response.family_id, response.name) == (Role.SYSTEM_ADMIN, None, "Caio")
    assert response.must_change_password is True
    assert uow.users.get_by_id(response.id).password_hash == FakePasswordHasher().hash("senha-temporaria")
    assert uow.committed is True


@pytest.mark.parametrize("role", [Role.FAMILY_ADMIN, Role.FAMILY_USER])
def test_create_family_user_in_an_existing_family(service: UserService, uow: FakeUnitOfWork, family, role):
    response = service.create_user(_create_dto(role=role, family_id=family.id))

    assert (response.role, response.family_id) == (role, family.id)
    assert uow.users.get_by_id(response.id) is not None


def test_create_user_in_unknown_family_raises_not_found(service: UserService, uow: FakeUnitOfWork):
    with pytest.raises(EntityNotFoundError):
        service.create_user(_create_dto(role=Role.FAMILY_USER, family_id=uuid.uuid4()))

    assert uow.users.users == {}


@pytest.mark.parametrize("role", [Role.FAMILY_ADMIN, Role.FAMILY_USER])
def test_create_family_user_without_family_raises_validation_error(service: UserService, role):
    with pytest.raises(DomainValidationError) as exc:
        service.create_user(_create_dto(role=role, family_id=None))

    assert exc.value.field == "family_id"


def test_create_system_admin_with_family_raises_validation_error(service: UserService, family):
    with pytest.raises(DomainValidationError) as exc:
        service.create_user(_create_dto(role=Role.SYSTEM_ADMIN, family_id=family.id))

    assert exc.value.field == "family_id"


def test_create_user_cannot_create_a_root(service: UserService, uow: FakeUnitOfWork):
    with pytest.raises(DomainValidationError, match="create-root") as exc:
        service.create_user(_create_dto(role=Role.ROOT))

    assert exc.value.field == "role"
    assert uow.users.users == {}


def test_create_user_requires_a_role(service: UserService):
    with pytest.raises(DomainValidationError, match="Papel do usuário é obrigatório"):
        service.create_user(_create_dto(role=None))


@pytest.mark.parametrize("overrides, message", [
    ({"name": "  "}, "Nome é obrigatório"),
    ({"name": None}, "Nome é obrigatório"),
    ({"username": ""}, "Nome de usuário é obrigatório"),
    ({"email": "  "}, "E-mail é obrigatório"),
    ({"temporary_password": "curta"}, "pelo menos 8 caracteres"),
    ({"temporary_password": None}, "Senha é obrigatória"),
])
def test_create_user_with_invalid_input_raises_and_saves_nothing(service, uow, overrides, message):
    with pytest.raises(DomainValidationError, match=message):
        service.create_user(_create_dto(**overrides))

    assert uow.users.users == {}
    assert uow.committed is False


def test_create_user_with_duplicate_username_ignoring_case_raises(service: UserService, uow: FakeUnitOfWork):
    _saved(uow, username="Caio", email="outro@example.com")

    with pytest.raises(EntityAlreadyExistsError) as exc:
        service.create_user(_create_dto(username="caio"))

    assert exc.value.field == "username"


def test_create_user_with_duplicate_email_ignoring_case_raises(service: UserService, uow: FakeUnitOfWork):
    _saved(uow, username="outro", email="CAIO@example.com")

    with pytest.raises(EntityAlreadyExistsError) as exc:
        service.create_user(_create_dto())

    assert exc.value.field == "email"


def test_username_is_unique_across_families(service: UserService, uow: FakeUnitOfWork, family):
    _saved(uow, family_id=uuid.uuid4(), username="caio", email="outro@example.com")

    with pytest.raises(EntityAlreadyExistsError):
        service.create_user(_create_dto(role=Role.FAMILY_USER, family_id=family.id))


# --- Leitura ---

def test_get_user(service: UserService, uow: FakeUnitOfWork):
    user = _saved(uow)

    response = service.get_user(user.id)

    assert (response.id, response.name, response.username, response.email) == (
        user.id, "Maria", "maria", "maria@example.com"
    )


def test_get_user_not_found(service: UserService):
    with pytest.raises(EntityNotFoundError):
        service.get_user(uuid.uuid4())


def test_user_response_never_exposes_the_password_hash(service: UserService, uow: FakeUnitOfWork):
    user = _saved(uow)

    assert not hasattr(service.get_user(user.id), "password_hash")


# --- Atualização ---

def test_update_user(service: UserService, uow: FakeUnitOfWork):
    user = _saved(uow)

    response = service.update_user(user.id, UpdateUserDTO(name="Maria Souza", username="msouza", email="m@example.com"))

    assert (response.name, response.username, response.email) == ("Maria Souza", "msouza", "m@example.com")
    assert uow.committed is True


def test_update_user_keeps_role_family_and_password(service: UserService, uow: FakeUnitOfWork):
    user = _saved(uow, role=Role.FAMILY_ADMIN, must_change_password=False)
    family_id = user.family_id

    service.update_user(user.id, UpdateUserDTO(name="Outra", username="outra", email="outra@example.com"))

    stored = uow.users.get_by_id(user.id)
    assert (stored.role, stored.family_id, stored.password_hash, stored.must_change_password) == (
        Role.FAMILY_ADMIN, family_id, "h", False
    )


def test_update_user_keeping_own_username_and_email_is_allowed(service: UserService, uow: FakeUnitOfWork):
    user = _saved(uow)

    response = service.update_user(user.id, UpdateUserDTO(name="Novo", username="MARIA", email="Maria@Example.com"))

    assert response.name == "Novo"


def test_update_user_to_another_users_username_raises(service: UserService, uow: FakeUnitOfWork):
    _saved(uow, name="João", username="joao", email="joao@example.com")
    other = _saved(uow)

    with pytest.raises(EntityAlreadyExistsError) as exc:
        service.update_user(other.id, UpdateUserDTO(name="Maria", username="JOAO", email="maria@example.com"))

    assert exc.value.field == "username"


def test_update_user_to_another_users_email_raises(service: UserService, uow: FakeUnitOfWork):
    _saved(uow, name="João", username="joao", email="joao@example.com")
    other = _saved(uow)

    with pytest.raises(EntityAlreadyExistsError) as exc:
        service.update_user(other.id, UpdateUserDTO(name="Maria", username="maria", email="JOAO@example.com"))

    assert exc.value.field == "email"


def test_update_user_with_blank_name_raises_and_keeps_current_data(service: UserService, uow: FakeUnitOfWork):
    user = _saved(uow)

    with pytest.raises(DomainValidationError, match="Nome é obrigatório"):
        service.update_user(user.id, UpdateUserDTO(name="  ", username="outro", email="outro@example.com"))

    stored = uow.users.get_by_id(user.id)
    assert (stored.name, stored.username, stored.email) == ("Maria", "maria", "maria@example.com")
    assert uow.committed is False


def test_update_root_allows_no_name(service: UserService, uow: FakeUnitOfWork):
    root = _saved_root(uow)

    response = service.update_user(root.id, UpdateUserDTO(name=None, username="root", email="novo@example.com"))

    assert (response.name, response.email) == (None, "novo@example.com")


def test_update_user_not_found(service: UserService):
    with pytest.raises(EntityNotFoundError):
        service.update_user(uuid.uuid4(), UpdateUserDTO(name="X", username="x", email="x@example.com"))


# --- Exclusão ---

def test_delete_user_success(service: UserService, uow: FakeUnitOfWork):
    user = _saved(uow)

    service.delete_user(user.id)

    assert uow.users.get_by_id(user.id) is None
    assert uow.committed is True


def test_delete_user_with_dependencies_raises_and_keeps_user(service: UserService, uow: FakeUnitOfWork):
    user = _saved(uow)
    uow.users.set_has_dependencies(True)

    with pytest.raises(EntityHasDependenciesError):
        service.delete_user(user.id)

    assert uow.users.get_by_id(user.id) is not None


def test_delete_root_is_blocked(service: UserService, uow: FakeUnitOfWork):
    root = _saved_root(uow)

    with pytest.raises(EntityHasDependenciesError, match="usuário root"):
        service.delete_user(root.id)

    assert uow.users.get_by_id(root.id) is not None


def test_delete_user_not_found(service: UserService):
    with pytest.raises(EntityNotFoundError):
        service.delete_user(uuid.uuid4())


def test_preview_user_deletion_without_dependencies(service: UserService, uow: FakeUnitOfWork):
    user = _saved(uow)

    preview = service.preview_user_deletion(user.id)

    assert (preview.name, preview.blocked_reason) == ("Maria", None)


def test_preview_user_deletion_with_dependencies_gives_the_reason(service: UserService, uow: FakeUnitOfWork):
    user = _saved(uow)
    uow.users.set_has_dependencies(True)

    preview = service.preview_user_deletion(user.id)

    assert preview.blocked_reason == str(user_has_dependencies(user.id))


def test_preview_root_deletion_is_blocked_and_named_by_username(service: UserService, uow: FakeUnitOfWork):
    root = _saved_root(uow)

    preview = service.preview_user_deletion(root.id)

    assert preview.name == "root"
    assert "usuário root" in preview.blocked_reason


def test_preview_user_deletion_not_found(service: UserService):
    with pytest.raises(EntityNotFoundError):
        service.preview_user_deletion(uuid.uuid4())


# --- Listagem: paginação, ordenação e pesquisa por nome, usuário e e-mail ---

def _names(result):
    return [item.name for item in result.items]


def _seed_people(uow) -> None:
    # Cada campo produz uma ordem diferente: nome (ana, Bruno, Zélia), usuário (Bruno, Zélia, ana),
    # e-mail (Zélia, ana, Bruno).
    _saved(uow, name="Zélia", username="bz.login", email="a.contato@mail.com")
    _saved(uow, name="ana", username="cz.apelido", email="m.correio@mail.com")
    _saved(uow, name="Bruno", username="az.nick", email="z.mensagem@mail.com")


def test_list_defaults_to_name_ascending_ignoring_case(service: UserService, uow: FakeUnitOfWork):
    _seed_people(uow)

    result = service.list_users_page()

    assert (result.sort_by, result.sort_dir) == ("name", "asc")
    assert _names(result) == ["ana", "Bruno", "Zélia"]


@pytest.mark.parametrize("field, ascending", [
    ("name", ["ana", "Bruno", "Zélia"]),
    ("username", ["Bruno", "Zélia", "ana"]),
    ("email", ["Zélia", "ana", "Bruno"]),
])
def test_list_sorts_by_each_sortable_field_in_both_directions(service, uow, field, ascending):
    _seed_people(uow)

    up = service.list_users_page(sort_by=field, sort_dir="asc")
    down = service.list_users_page(sort_by=field, sort_dir="desc")

    assert (up.sort_by, up.sort_dir) == (field, "asc")
    assert (down.sort_by, down.sort_dir) == (field, "desc")
    assert _names(up) == ascending
    assert _names(down) == ascending[::-1]


@pytest.mark.parametrize("sort_by", ["role", "family", "password_hash", "", "NAME", None])
def test_list_only_sorts_by_name_username_or_email(service: UserService, uow: FakeUnitOfWork, sort_by):
    _seed_people(uow)

    assert service.list_users_page(sort_by=sort_by).sort_by == "name"


@pytest.mark.parametrize("sort_dir", ["up", "", "DESC", 1, None])
def test_invalid_direction_falls_back_to_ascending(service: UserService, uow: FakeUnitOfWork, sort_dir):
    _seed_people(uow)

    result = service.list_users_page(sort_dir=sort_dir)

    assert result.sort_dir == "asc"
    assert _names(result) == ["ana", "Bruno", "Zélia"]


def test_root_without_name_comes_first_when_sorting_by_name(service: UserService, uow: FakeUnitOfWork):
    _seed_people(uow)
    _saved_root(uow)

    assert _names(service.list_users_page()) == [None, "ana", "Bruno", "Zélia"]


def test_pagination_slices_the_sorted_listing(service: UserService, uow: FakeUnitOfWork):
    for n in range(1, 16):
        _saved(uow, name=f"Pessoa {n:02d}", username=f"pessoa{n:02d}", email=f"p{n:02d}@example.com")

    second = service.list_users_page(page=2)

    assert (second.page, second.total, second.total_pages) == (2, 15, 2)
    assert _names(second) == [f"Pessoa {n:02d}" for n in range(11, 16)]


def test_page_beyond_the_last_returns_the_last_page(service: UserService, uow: FakeUnitOfWork):
    for n in range(1, 13):
        _saved(uow, name=f"Pessoa {n:02d}", username=f"pessoa{n:02d}", email=f"p{n:02d}@example.com")

    result = service.list_users_page(page=9)

    assert result.page == 2
    assert len(result.items) == 2


@pytest.mark.parametrize("term, expected", [
    ("zel", ["Zélia"]),                       # nome (sem acento e sem caixa)
    ("APELIDO", ["ana"]),                     # nome de usuário
    ("mensagem", ["Bruno"]),                  # e-mail
    ("mail", ["ana", "Bruno", "Zélia"]),      # todos, pelo e-mail
])
def test_search_covers_name_username_and_email(service: UserService, uow: FakeUnitOfWork, term, expected):
    _seed_people(uow)

    result = service.list_users_page(search=term)

    assert result.search == term
    assert _names(result) == expected


def test_search_does_not_look_at_other_fields(service: UserService, uow: FakeUnitOfWork):
    _saved(uow, password_hash="segredo-hash")

    assert service.list_users_page(search="segredo").total == 0
    assert service.list_users_page(search="FAMILY_USER").total == 0


def test_search_paginates_over_the_results_and_keeps_sorting(service: UserService, uow: FakeUnitOfWork):
    for n in range(1, 13):
        _saved(uow, name=f"Silva {n:02d}", username=f"silva{n:02d}", email=f"s{n:02d}@example.com")
    for n in range(1, 30):
        _saved(uow, name=f"Souza {n:02d}", username=f"souza{n:02d}", email=f"z{n:02d}@example.com")

    second = service.list_users_page(page=2, sort_dir="desc", search="silva")

    assert (second.total, second.total_pages) == (12, 2)
    assert _names(second) == ["Silva 02", "Silva 01"]


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_blank_search_means_no_filter(service: UserService, uow: FakeUnitOfWork, raw):
    _seed_people(uow)

    result = service.list_users_page(search=raw)

    assert (result.search, result.total) == ("", 3)
