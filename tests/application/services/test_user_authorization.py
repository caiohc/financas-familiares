"""
Tentativas de burlar a hierarquia de contas pelo serviço: usuário comum, administrador de outra família,
escalada de privilégio, ações sobre o root e vazamento de existência (403 x 404).
"""
import uuid

import pytest

from application.dtos.identity_dtos import CreateUserDTO, UpdateUserDTO
from domain.identity.entities import Role
from domain.identity.policy import Principal
from domain.shared.exceptions import AccessDeniedError, EntityNotFoundError
from fakes.identity_builders import make_family, make_user, principal_of


@pytest.fixture
def family_a(uow):
    return make_family(uow, "Família A")


@pytest.fixture
def family_b(uow):
    return make_family(uow, "Família B")


@pytest.fixture
def world(uow, family_a, family_b):
    """Um ambiente com um usuário de cada papel e de cada família."""
    return {
        "root": make_user(uow, Role.ROOT, username="root"),
        "sysadmin": make_user(uow, Role.SYSTEM_ADMIN, username="sysadmin"),
        "sysadmin2": make_user(uow, Role.SYSTEM_ADMIN, username="sysadmin2"),
        "admin_a": make_user(uow, Role.FAMILY_ADMIN, family=family_a, username="admin_a"),
        "user_a": make_user(uow, Role.FAMILY_USER, family=family_a, username="user_a"),
        "pending_a": make_user(uow, Role.FAMILY_USER, family=family_a, username="pending_a", activated=False),
        "admin_b": make_user(uow, Role.FAMILY_ADMIN, family=family_b, username="admin_b"),
        "user_b": make_user(uow, Role.FAMILY_USER, family=family_b, username="user_b"),
        "pending_b": make_user(uow, Role.FAMILY_USER, family=family_b, username="pending_b", activated=False),
    }


def _create(role, family_id=None, username="novo"):
    return CreateUserDTO(
        role=role, family_id=family_id, name="Novo", username=username, email=f"{username}@example.com",
        email_confirmation=f"{username}@example.com",
    )


def _update(user):
    return UpdateUserDTO(name="Outro Nome", username=user.username, email=user.email)


# Cada operação sobre um usuário-alvo, como (nome, chamada)
OPERATIONS = {
    "get": lambda s, actor, target: s.get_user(actor, target.id),
    "update": lambda s, actor, target: s.update_user(actor, target.id, _update(target)),
    "deactivate": lambda s, actor, target: s.deactivate_user(actor, target.id),
    "reactivate": lambda s, actor, target: s.reactivate_user(actor, target.id),
    "delete": lambda s, actor, target: s.delete_user(actor, target.id),
    "preview_delete": lambda s, actor, target: s.preview_user_deletion(actor, target.id),
    "issue_invitation": lambda s, actor, target: s.issue_invitation(actor, target.id),
}


# ---------------------------------------------------------------------------
# Usuário de família comum: nenhuma operação de administração
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("operation", sorted(OPERATIONS))
@pytest.mark.parametrize("target_key", ["user_a", "admin_a", "sysadmin", "root"])
def test_a_family_user_cannot_do_anything_to_any_account(user_service, world, operation, target_key):
    actor = principal_of(world["user_a"])

    with pytest.raises(AccessDeniedError):
        OPERATIONS[operation](user_service, actor, world[target_key])


def test_a_family_user_cannot_create_anyone(user_service, uow, world, family_a):
    users_before = len(uow.users.users)

    for role in (Role.FAMILY_USER, Role.FAMILY_ADMIN, Role.SYSTEM_ADMIN):
        with pytest.raises(AccessDeniedError):
            user_service.create_user(principal_of(world["user_a"]), _create(role, family_a.id if role is not Role.SYSTEM_ADMIN else None))

    assert len(uow.users.users) == users_before


def test_a_family_user_cannot_list_users(user_service, world):
    with pytest.raises(AccessDeniedError):
        user_service.list_users_page(principal_of(world["user_a"]))


# ---------------------------------------------------------------------------
# Administrador de família: só a própria família
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("operation", sorted(OPERATIONS))
@pytest.mark.parametrize("target_key", ["user_b", "admin_b", "pending_b"])
def test_family_admin_does_not_even_see_users_of_another_family(user_service, world, operation, target_key):
    actor = principal_of(world["admin_a"])

    with pytest.raises(EntityNotFoundError):
        OPERATIONS[operation](user_service, actor, world[target_key])


@pytest.mark.parametrize("operation", sorted(OPERATIONS))
@pytest.mark.parametrize("target_key", ["sysadmin", "sysadmin2", "root"])
def test_family_admin_does_not_even_see_system_level_users(user_service, world, operation, target_key):
    with pytest.raises(EntityNotFoundError):
        OPERATIONS[operation](user_service, principal_of(world["admin_a"]), world[target_key])


@pytest.mark.parametrize("operation", ["get", "update", "deactivate", "reactivate", "preview_delete"])
@pytest.mark.parametrize("target_key", ["user_a", "admin_a2"])
def test_family_admin_manages_users_of_its_own_family(user_service, uow, world, family_a, operation, target_key):
    world["admin_a2"] = make_user(uow, Role.FAMILY_ADMIN, family=family_a, username="admin_a2")
    actor = principal_of(world["admin_a"])

    OPERATIONS[operation](user_service, actor, world[target_key])       # não levanta


def test_family_admin_reissues_the_invitation_of_a_pending_user_of_its_own_family(user_service, world):
    issued = user_service.issue_invitation(principal_of(world["admin_a"]), world["pending_a"].id)
    assert issued.user.id == world["pending_a"].id


def test_family_admin_cannot_create_in_another_family(user_service, uow, world, family_b):
    users_before = len(uow.users.users)

    with pytest.raises(AccessDeniedError):
        user_service.create_user(principal_of(world["admin_a"]), _create(Role.FAMILY_USER, family_b.id))

    assert len(uow.users.users) == users_before


def test_family_admin_cannot_escalate_by_creating_a_system_admin(user_service, uow, world):
    users_before = len(uow.users.users)

    with pytest.raises(AccessDeniedError):
        user_service.create_user(principal_of(world["admin_a"]), _create(Role.SYSTEM_ADMIN))

    assert len(uow.users.users) == users_before


def test_nobody_creates_a_root_not_even_a_family_admin_trying_to_escalate(user_service, uow, world):
    from domain.shared.exceptions import DomainValidationError

    users_before = len(uow.users.users)

    with pytest.raises(DomainValidationError, match="create-root"):
        user_service.create_user(principal_of(world["admin_a"]), _create(Role.ROOT))

    assert len(uow.users.users) == users_before


def test_family_admin_cannot_create_a_user_with_no_family_to_dodge_the_check(user_service, uow, world):
    users_before = len(uow.users.users)

    with pytest.raises(AccessDeniedError):
        user_service.create_user(principal_of(world["admin_a"]), _create(Role.FAMILY_USER, None))

    assert len(uow.users.users) == users_before


def test_family_admin_creates_in_its_own_family(user_service, world, family_a):
    issued = user_service.create_user(principal_of(world["admin_a"]), _create(Role.FAMILY_ADMIN, family_a.id))
    assert issued.user.family_id == family_a.id


def test_family_admin_listing_is_scoped_to_its_family(user_service, world, family_a):
    page = user_service.list_users_page(principal_of(world["admin_a"]))

    assert {u.username for u in page.items} == {"admin_a", "user_a", "pending_a"}
    assert page.total == 3
    assert all(u.family_id == family_a.id for u in page.items)


def test_family_admin_search_never_reaches_other_families(user_service, world):
    page = user_service.list_users_page(principal_of(world["admin_a"]), search="user_b")
    assert page.total == 0 and page.items == []

    page = user_service.list_users_page(principal_of(world["admin_a"]), search="sysadmin")
    assert page.total == 0


def test_family_admin_pagination_total_does_not_count_other_families(user_service, world):
    page = user_service.list_users_page(principal_of(world["admin_a"]), page=1, page_size=10)
    assert page.total == 3


def test_nonexistent_and_invisible_users_look_the_same_to_a_family_admin(user_service, world):
    actor = principal_of(world["admin_a"])
    with pytest.raises(EntityNotFoundError) as invisible:
        user_service.get_user(actor, world["user_b"].id)
    with pytest.raises(EntityNotFoundError) as missing:
        user_service.get_user(actor, uuid.uuid4())

    assert type(invisible.value) is type(missing.value)
    # a mesma mensagem, só mudando o id pedido: nada denuncia que o usuário existe em outra família
    assert str(invisible.value).replace(str(world["user_b"].id), "ID") == str(missing.value).replace(str(missing.value.entity_id), "ID")


# ---------------------------------------------------------------------------
# Administrador do sistema
# ---------------------------------------------------------------------------

def test_system_admin_cannot_delete_the_root(user_service, uow, world):
    from domain.shared.exceptions import EntityHasDependenciesError

    with pytest.raises(EntityHasDependenciesError, match="usuário root"):
        user_service.delete_user(principal_of(world["sysadmin"]), world["root"].id)

    assert uow.users.get_by_id(world["root"].id) is not None


@pytest.mark.parametrize("operation", ["update", "deactivate", "reactivate", "issue_invitation"])
def test_system_admin_cannot_touch_the_root_and_nothing_changes(uow, user_service, world, operation):
    root = world["root"]
    before = (root.password_hash, root.is_active, root.name, root.username, root.email)

    with pytest.raises(AccessDeniedError):
        OPERATIONS[operation](user_service, principal_of(world["sysadmin"]), root)

    assert (root.password_hash, root.is_active, root.name, root.username, root.email) == before


def test_system_admin_manages_any_family(user_service, world):
    actor = principal_of(world["sysadmin"])
    for key in ("user_a", "user_b", "admin_a", "admin_b"):
        user_service.get_user(actor, world[key].id)
        user_service.deactivate_user(actor, world[key].id)


def test_system_admin_sees_everyone_in_the_listing(user_service, world):
    page = user_service.list_users_page(principal_of(world["sysadmin"]), page_size=50)
    assert page.total == len(world)


def test_system_admin_creates_any_role_but_root(user_service, world, family_a):
    actor = principal_of(world["sysadmin"])
    assert user_service.create_user(actor, _create(Role.SYSTEM_ADMIN, username="a1")).user.role is Role.SYSTEM_ADMIN
    assert user_service.create_user(actor, _create(Role.FAMILY_ADMIN, family_a.id, "a2")).user.role is Role.FAMILY_ADMIN
    assert user_service.create_user(actor, _create(Role.FAMILY_USER, family_a.id, "a3")).user.role is Role.FAMILY_USER


# ---------------------------------------------------------------------------
# Root: só administra administradores do sistema
# ---------------------------------------------------------------------------

def test_root_creates_only_system_admins(user_service, uow, world, family_a):
    actor = principal_of(world["root"])
    users_before = len(uow.users.users)

    assert user_service.create_user(actor, _create(Role.SYSTEM_ADMIN)).user.role is Role.SYSTEM_ADMIN
    for role in (Role.FAMILY_ADMIN, Role.FAMILY_USER):
        with pytest.raises(AccessDeniedError):
            user_service.create_user(actor, _create(role, family_a.id, username=f"x{role.value.lower()}"))

    assert len(uow.users.users) == users_before + 1


@pytest.mark.parametrize("operation", ["update", "deactivate", "delete", "issue_invitation"])
@pytest.mark.parametrize("target_key", ["admin_a", "user_a", "pending_a"])
def test_root_sees_but_cannot_manage_family_users(user_service, world, operation, target_key):
    with pytest.raises(AccessDeniedError):
        OPERATIONS[operation](user_service, principal_of(world["root"]), world[target_key])


def test_root_manages_system_admins(user_service, world):
    actor = principal_of(world["root"])
    user_service.update_user(actor, world["sysadmin"].id, _update(world["sysadmin"]))
    user_service.deactivate_user(actor, world["sysadmin"].id)
    user_service.issue_invitation(actor, world["sysadmin2"].id)


def test_root_cannot_act_on_itself(user_service, world):
    actor = principal_of(world["root"])
    with pytest.raises(AccessDeniedError):
        user_service.issue_invitation(actor, world["root"].id)
    with pytest.raises(AccessDeniedError):
        user_service.update_user(actor, world["root"].id, _update(world["root"]))


# ---------------------------------------------------------------------------
# Principal forjado ou inconsistente
# ---------------------------------------------------------------------------

def test_a_family_admin_principal_without_a_family_gets_nothing(user_service, world):
    """Defesa: família None do ator não pode 'casar' com família None de ninguém."""
    broken = Principal(user_id=uuid.uuid4(), role=Role.FAMILY_ADMIN, family_id=None)

    # Sem a negação na porta de entrada, a listagem ficaria sem o filtro do tenant e mostraria todos.
    with pytest.raises(AccessDeniedError):
        user_service.list_users_page(broken)
    for key in ("sysadmin", "root", "user_a", "admin_b"):
        with pytest.raises(AccessDeniedError):
            user_service.get_user(broken, world[key].id)
        with pytest.raises(AccessDeniedError):
            user_service.issue_invitation(broken, world[key].id)
    with pytest.raises(AccessDeniedError):
        user_service.create_user(broken, _create(Role.FAMILY_USER, None))


def test_a_principal_with_an_unknown_role_is_denied(user_service, world):
    bogus = Principal(user_id=uuid.uuid4(), role="SUPERUSER", family_id=None)

    with pytest.raises(AccessDeniedError):
        user_service.list_users_page(bogus)
    with pytest.raises(AccessDeniedError):
        user_service.create_user(bogus, _create(Role.SYSTEM_ADMIN))
