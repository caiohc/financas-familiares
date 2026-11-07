"""Matriz de permissões das contas. É o contrato: cada linha foi decidida; mudar uma exige decidir de novo."""
import uuid
from types import SimpleNamespace

import pytest

from domain.identity import policy
from domain.identity.entities import Role
from domain.identity.policy import Principal

FAMILY_A = uuid.uuid4()
FAMILY_B = uuid.uuid4()


def _actor(role, family_id=None) -> Principal:
    return Principal(user_id=uuid.uuid4(), role=role, family_id=family_id)


ROOT = _actor(Role.ROOT)
SYSTEM_ADMIN = _actor(Role.SYSTEM_ADMIN)
FAMILY_ADMIN_A = _actor(Role.FAMILY_ADMIN, FAMILY_A)
FAMILY_USER_A = _actor(Role.FAMILY_USER, FAMILY_A)


def _target(role, family_id=None, user_id=None):
    return SimpleNamespace(id=user_id or uuid.uuid4(), role=role, family_id=family_id)


# --- Acesso à área de usuários ---

@pytest.mark.parametrize("actor, allowed", [
    (ROOT, True), (SYSTEM_ADMIN, True), (FAMILY_ADMIN_A, True), (FAMILY_USER_A, False),
])
def test_only_administrators_manage_users(actor, allowed):
    assert policy.can_manage_users(actor) is allowed


# --- Cadastrar ---

@pytest.mark.parametrize("actor, role, family_id, allowed", [
    # root: só administradores do sistema
    (ROOT, Role.SYSTEM_ADMIN, None, True),
    (ROOT, Role.FAMILY_ADMIN, FAMILY_A, False),
    (ROOT, Role.FAMILY_USER, FAMILY_A, False),
    (ROOT, Role.ROOT, None, False),
    # administrador do sistema: qualquer papel, exceto root, em qualquer família
    (SYSTEM_ADMIN, Role.SYSTEM_ADMIN, None, True),
    (SYSTEM_ADMIN, Role.FAMILY_ADMIN, FAMILY_A, True),
    (SYSTEM_ADMIN, Role.FAMILY_ADMIN, FAMILY_B, True),
    (SYSTEM_ADMIN, Role.FAMILY_USER, FAMILY_B, True),
    (SYSTEM_ADMIN, Role.ROOT, None, False),
    # administrador de família: só na própria família, nunca nível de sistema
    (FAMILY_ADMIN_A, Role.FAMILY_ADMIN, FAMILY_A, True),
    (FAMILY_ADMIN_A, Role.FAMILY_USER, FAMILY_A, True),
    (FAMILY_ADMIN_A, Role.FAMILY_USER, FAMILY_B, False),     # outra família
    (FAMILY_ADMIN_A, Role.FAMILY_USER, None, False),         # sem família
    (FAMILY_ADMIN_A, Role.SYSTEM_ADMIN, None, False),        # escalada de privilégio
    (FAMILY_ADMIN_A, Role.ROOT, None, False),
    # usuário de família: ninguém
    (FAMILY_USER_A, Role.FAMILY_USER, FAMILY_A, False),
    (FAMILY_USER_A, Role.FAMILY_ADMIN, FAMILY_A, False),
    (FAMILY_USER_A, Role.SYSTEM_ADMIN, None, False),
])
def test_can_create_user(actor, role, family_id, allowed):
    assert policy.can_create_user(actor, role, family_id) is allowed


@pytest.mark.parametrize("role", [None, "SYSTEM_ADMIN", 1, ""])
def test_cannot_create_with_an_invalid_role(role):
    assert policy.can_create_user(SYSTEM_ADMIN, role, None) is False


def test_creatable_roles_per_actor():
    assert policy.creatable_roles(ROOT) == (Role.SYSTEM_ADMIN,)
    assert Role.ROOT not in policy.creatable_roles(SYSTEM_ADMIN)
    assert set(policy.creatable_roles(SYSTEM_ADMIN)) == {Role.SYSTEM_ADMIN, Role.FAMILY_ADMIN, Role.FAMILY_USER}
    assert set(policy.creatable_roles(FAMILY_ADMIN_A)) == {Role.FAMILY_ADMIN, Role.FAMILY_USER}
    assert policy.creatable_roles(FAMILY_USER_A) == ()


# --- Ver ---

@pytest.mark.parametrize("actor, target, allowed", [
    (ROOT, _target(Role.FAMILY_USER, FAMILY_B), True),
    (SYSTEM_ADMIN, _target(Role.FAMILY_USER, FAMILY_B), True),
    (SYSTEM_ADMIN, _target(Role.ROOT), True),
    (FAMILY_ADMIN_A, _target(Role.FAMILY_USER, FAMILY_A), True),
    (FAMILY_ADMIN_A, _target(Role.FAMILY_USER, FAMILY_B), False),     # outra família: não existe para ele
    (FAMILY_ADMIN_A, _target(Role.SYSTEM_ADMIN), False),
    (FAMILY_ADMIN_A, _target(Role.ROOT), False),
    (FAMILY_USER_A, _target(Role.FAMILY_USER, FAMILY_A), False),
])
def test_can_view_user(actor, target, allowed):
    assert policy.can_view_user(actor, target) is allowed


# --- Gerenciar (editar, desativar, reativar, excluir) ---

@pytest.mark.parametrize("actor, target, allowed", [
    (ROOT, _target(Role.SYSTEM_ADMIN), True),
    (ROOT, _target(Role.FAMILY_ADMIN, FAMILY_A), False),              # o root só administra administradores do sistema
    (ROOT, _target(Role.FAMILY_USER, FAMILY_A), False),
    (ROOT, _target(Role.ROOT), False),
    (SYSTEM_ADMIN, _target(Role.SYSTEM_ADMIN), True),
    (SYSTEM_ADMIN, _target(Role.FAMILY_ADMIN, FAMILY_B), True),
    (SYSTEM_ADMIN, _target(Role.FAMILY_USER, FAMILY_A), True),
    (SYSTEM_ADMIN, _target(Role.ROOT), False),                        # ninguém age sobre o root pela aplicação
    (FAMILY_ADMIN_A, _target(Role.FAMILY_USER, FAMILY_A), True),
    (FAMILY_ADMIN_A, _target(Role.FAMILY_ADMIN, FAMILY_A), True),
    (FAMILY_ADMIN_A, _target(Role.FAMILY_USER, FAMILY_B), False),
    (FAMILY_ADMIN_A, _target(Role.FAMILY_ADMIN, FAMILY_B), False),
    (FAMILY_ADMIN_A, _target(Role.SYSTEM_ADMIN), False),
    (FAMILY_ADMIN_A, _target(Role.ROOT), False),
    (FAMILY_USER_A, _target(Role.FAMILY_USER, FAMILY_A), False),
])
def test_can_manage_user(actor, target, allowed):
    assert policy.can_manage_user(actor, target) is allowed


# --- Emitir convite (ativação / redefinição de administrador do sistema) ---

@pytest.mark.parametrize("actor, target, allowed", [
    # alvo administrador do sistema: só outro administrador do sistema (ou o root)
    (SYSTEM_ADMIN, _target(Role.SYSTEM_ADMIN), True),
    (ROOT, _target(Role.SYSTEM_ADMIN), True),
    (FAMILY_ADMIN_A, _target(Role.SYSTEM_ADMIN), False),
    (FAMILY_USER_A, _target(Role.SYSTEM_ADMIN), False),
    # alvo usuário/administrador de família
    (SYSTEM_ADMIN, _target(Role.FAMILY_ADMIN, FAMILY_B), True),
    (SYSTEM_ADMIN, _target(Role.FAMILY_USER, FAMILY_A), True),
    (FAMILY_ADMIN_A, _target(Role.FAMILY_USER, FAMILY_A), True),
    (FAMILY_ADMIN_A, _target(Role.FAMILY_ADMIN, FAMILY_A), True),
    (FAMILY_ADMIN_A, _target(Role.FAMILY_USER, FAMILY_B), False),     # outra família
    (ROOT, _target(Role.FAMILY_USER, FAMILY_A), False),
    (FAMILY_USER_A, _target(Role.FAMILY_USER, FAMILY_A), False),
    # ninguém emite convite para o root
    (ROOT, _target(Role.ROOT), False),
    (SYSTEM_ADMIN, _target(Role.ROOT), False),
])
def test_can_issue_invitation(actor, target, allowed):
    assert policy.can_issue_invitation(actor, target) is allowed


@pytest.mark.parametrize("role, family_id", [
    (Role.SYSTEM_ADMIN, None), (Role.FAMILY_ADMIN, FAMILY_A), (Role.ROOT, None),
])
def test_nobody_issues_an_invitation_for_themselves(role, family_id):
    me = _actor(role, family_id)
    assert policy.can_issue_invitation(me, _target(role, family_id, user_id=me.user_id)) is False


def test_family_admin_of_another_family_has_no_power_over_this_one():
    outsider = _actor(Role.FAMILY_ADMIN, FAMILY_B)
    target = _target(Role.FAMILY_USER, FAMILY_A)
    assert not policy.can_view_user(outsider, target)
    assert not policy.can_manage_user(outsider, target)
    assert not policy.can_issue_invitation(outsider, target)


def test_a_family_actor_without_family_never_matches_a_target_without_family():
    """Defesa: família None não pode 'casar' com família None e liberar acesso por engano."""
    broken = Principal(user_id=uuid.uuid4(), role=Role.FAMILY_ADMIN, family_id=None)
    target = _target(Role.FAMILY_USER, None)
    assert not policy.can_view_user(broken, target)
    assert not policy.can_manage_user(broken, target)
    assert not policy.can_issue_invitation(broken, target)
    assert not policy.can_create_user(broken, Role.FAMILY_USER, None)


def test_a_family_admin_without_a_family_cannot_manage_users_at_all():
    """Sem este filtro, a listagem ficaria sem o escopo do tenant e mostraria todos os usuários."""
    assert policy.can_manage_users(Principal(user_id=uuid.uuid4(), role=Role.FAMILY_ADMIN, family_id=None)) is False
