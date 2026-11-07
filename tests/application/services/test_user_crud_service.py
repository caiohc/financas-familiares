"""CRUD de usuário feito por um administrador: cadastro com convite, listagem, edição, situação e exclusão."""
import uuid
from datetime import timedelta

import pytest

from application.dtos.identity_dtos import CreateUserDTO, UpdateUserDTO
from domain.identity.entities import AccountStatus, Role
from domain.identity.exceptions import user_has_dependencies
from domain.identity.invitations import InvitationPurpose, normalize_code
from domain.shared.exceptions import (
    AccessDeniedError,
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)
from fakes.identity_builders import make_family, make_user, principal_of
from fakes.identity_fakes import token_from_link


@pytest.fixture
def family(uow):
    return make_family(uow, "Silva")


@pytest.fixture
def sysadmin(uow):
    return make_user(uow, Role.SYSTEM_ADMIN, username="sysadmin")


@pytest.fixture
def actor(sysadmin):
    return principal_of(sysadmin)


def _dto(**overrides) -> CreateUserDTO:
    data = dict(
        role=Role.SYSTEM_ADMIN, family_id=None, name="Caio", username="caio", email="caio@example.com",
        email_confirmation="caio@example.com",
    )
    data.update(overrides)
    return CreateUserDTO(**data)


# ---------------------------------------------------------------------------
# Cadastro: conta pendente + convite (o administrador nunca define a senha)
# ---------------------------------------------------------------------------

def test_create_system_admin_leaves_a_pending_account_without_password(user_service, uow, actor):
    issued = user_service.create_user(actor, _dto())

    assert (issued.user.role, issued.user.family_id, issued.user.name) == (Role.SYSTEM_ADMIN, None, "Caio")
    assert issued.user.status is AccountStatus.PENDING
    assert issued.user.is_pending is True
    stored = uow.users.get_by_id(issued.user.id)
    assert stored.password_hash is None and stored.activated_at is None
    assert uow.committed is True


@pytest.mark.parametrize("role", [Role.FAMILY_ADMIN, Role.FAMILY_USER])
def test_create_family_user_in_an_existing_family(user_service, uow, actor, family, role):
    issued = user_service.create_user(actor, _dto(role=role, family_id=family.id))

    assert (issued.user.role, issued.user.family_id) == (role, family.id)
    assert uow.users.get_by_id(issued.user.id).is_pending


def test_create_user_issues_an_activation_invitation_with_a_code(user_service, uow, hasher, actor, clock):
    issued = user_service.create_user(actor, _dto())

    invitation = uow.invitations.get_active_for_user(issued.user.id)
    assert invitation.purpose is InvitationPurpose.ACTIVATION
    assert invitation.created_by_user_id == actor.user_id
    assert invitation.created_at == clock.now
    assert invitation.expires_at == clock.now + timedelta(hours=24)
    assert issued.expires_at == invitation.expires_at
    # o banco guarda só o hash do código; o código em si só existe na resposta
    assert hasher.verify(normalize_code(issued.code), invitation.code_hash)
    assert invitation.code_hash != issued.code


def test_the_code_is_shown_in_the_response_but_never_stored_or_emailed(user_service, uow, emails, actor):
    issued = user_service.create_user(actor, _dto())

    raw = normalize_code(issued.code)
    assert len(raw) == 8
    stored = uow.invitations.get_active_for_user(issued.user.id)
    assert stored.code_hash not in (raw, issued.code)        # o que fica gravado é o hash, não o código
    mail = emails.last
    assert raw not in mail["body"] and issued.code not in mail["body"] and raw not in mail["subject"]


def test_the_email_goes_to_the_informed_address_with_the_activation_link(user_service, emails, actor):
    issued = user_service.create_user(actor, _dto())

    assert issued.email_sent is True
    assert emails.last["to"] == "caio@example.com"
    assert "https://app.test/auth/activate/" in emails.last["body"]
    assert "Caio" in emails.last["body"]


def test_the_emailed_token_matches_the_stored_invitation(user_service, uow, emails, actor):
    from domain.identity.invitations import hash_token

    issued = user_service.create_user(actor, _dto())

    token = token_from_link(emails.last["body"])
    assert uow.invitations.get_by_token_hash(hash_token(token)).user_id == issued.user.id
    assert uow.invitations.get_active_for_user(issued.user.id).token_hash == hash_token(token)


def test_the_email_never_carries_a_password(user_service, emails, actor):
    user_service.create_user(actor, _dto())

    assert "senha:" not in emails.last["body"].lower()


def test_create_user_keeps_the_account_when_the_email_cannot_be_sent(user_service, uow, emails, actor):
    emails.fail = True

    issued = user_service.create_user(actor, _dto())

    assert issued.email_sent is False
    assert uow.users.get_by_id(issued.user.id) is not None
    assert uow.invitations.get_active_for_user(issued.user.id) is not None
    assert issued.code            # o administrador ainda recebe o código e pode reenviar o convite


def test_create_user_strips_username_and_normalizes_email(user_service, actor):
    issued = user_service.create_user(
        actor, _dto(username="  caio  ", email="  Caio@Example.COM ", email_confirmation="caio@example.com"),
    )
    assert (issued.user.username, issued.user.email) == ("caio", "Caio@example.com")


def test_create_user_in_unknown_family_raises_not_found_and_saves_nothing(user_service, uow, actor):
    users_before = len(uow.users.users)
    with pytest.raises(EntityNotFoundError):
        user_service.create_user(actor, _dto(role=Role.FAMILY_USER, family_id=uuid.uuid4()))
    assert len(uow.users.users) == users_before


@pytest.mark.parametrize("role", [Role.FAMILY_ADMIN, Role.FAMILY_USER])
def test_create_family_user_without_family_raises_validation_error(user_service, actor, role):
    with pytest.raises(DomainValidationError) as exc:
        user_service.create_user(actor, _dto(role=role, family_id=None))
    assert exc.value.field == "family_id"


def test_create_system_admin_with_family_raises_validation_error(user_service, actor, family):
    with pytest.raises(DomainValidationError) as exc:
        user_service.create_user(actor, _dto(role=Role.SYSTEM_ADMIN, family_id=family.id))
    assert exc.value.field == "family_id"


def test_nobody_creates_a_root_through_the_application(user_service, uow, actor):
    with pytest.raises(DomainValidationError, match="create-root") as exc:
        user_service.create_user(actor, _dto(role=Role.ROOT))
    assert exc.value.field == "role"


def test_create_user_requires_a_role(user_service, actor):
    with pytest.raises(DomainValidationError, match="Papel do usuário é obrigatório"):
        user_service.create_user(actor, _dto(role=None))


@pytest.mark.parametrize("overrides, message", [
    ({"name": "  "}, "Nome é obrigatório"),
    ({"name": None}, "Nome é obrigatório"),
    ({"username": ""}, "Nome de usuário é obrigatório"),
    ({"email": "  ", "email_confirmation": "  "}, "E-mail é obrigatório"),
    ({"email": "invalido", "email_confirmation": "invalido"}, "e-mail válido"),
])
def test_create_user_with_invalid_input_raises_and_saves_nothing(user_service, uow, emails, actor, overrides, message):
    users_before = len(uow.users.users)

    with pytest.raises(DomainValidationError, match=message):
        user_service.create_user(actor, _dto(**overrides))

    assert len(uow.users.users) == users_before
    assert uow.invitations.invitations == {}
    assert emails.outbox == []


@pytest.mark.parametrize("confirmation", ["outro@example.com", "caio@example.co", "", None])
def test_create_user_with_mismatching_email_confirmation_saves_nothing_and_sends_nothing(
    user_service, uow, emails, actor, confirmation,
):
    users_before = len(uow.users.users)

    with pytest.raises(DomainValidationError, match="e-mails informados não conferem") as exc:
        user_service.create_user(actor, _dto(email_confirmation=confirmation))

    assert exc.value.field == "email_confirmation"
    assert len(uow.users.users) == users_before
    assert uow.invitations.invitations == {} and emails.outbox == []


def test_email_confirmation_ignores_case_and_edges(user_service, actor):
    issued = user_service.create_user(actor, _dto(email="caio@example.com", email_confirmation="  CAIO@Example.com "))
    assert issued.user.email == "caio@example.com"


def test_create_user_with_duplicate_username_ignoring_case_raises(user_service, uow, emails, actor):
    make_user(uow, Role.FAMILY_USER, username="Caio", email="outro@example.com")

    with pytest.raises(EntityAlreadyExistsError) as exc:
        user_service.create_user(actor, _dto(username="caio"))

    assert exc.value.field == "username"
    assert emails.outbox == []


def test_create_user_with_duplicate_email_ignoring_case_raises(user_service, uow, emails, actor):
    make_user(uow, Role.FAMILY_USER, username="outro", email="CAIO@example.com")

    with pytest.raises(EntityAlreadyExistsError) as exc:
        user_service.create_user(actor, _dto())

    assert exc.value.field == "email"
    assert emails.outbox == []


def test_username_is_unique_across_families(user_service, uow, actor, family):
    make_user(uow, Role.FAMILY_USER, username="caio", email="outro@example.com")

    with pytest.raises(EntityAlreadyExistsError):
        user_service.create_user(actor, _dto(role=Role.FAMILY_USER, family_id=family.id))


# ---------------------------------------------------------------------------
# Leitura e listagem
# ---------------------------------------------------------------------------

def test_get_user(user_service, uow, actor):
    user = make_user(uow, name="Maria", username="maria", email="maria@example.com")

    response = user_service.get_user(actor, user.id)

    assert (response.id, response.name, response.username, response.email) == (
        user.id, "Maria", "maria", "maria@example.com"
    )


def test_get_user_not_found(user_service, actor):
    with pytest.raises(EntityNotFoundError):
        user_service.get_user(actor, uuid.uuid4())


def test_user_response_never_exposes_the_password_hash(user_service, uow, actor):
    user = make_user(uow)

    response = user_service.get_user(actor, user.id)

    assert not hasattr(response, "password_hash")
    assert user.password_hash not in repr(response)


# ---------------------------------------------------------------------------
# Atualização
# ---------------------------------------------------------------------------

def test_update_user(user_service, uow, actor):
    user = make_user(uow, activated=False)

    response = user_service.update_user(
        actor, user.id, UpdateUserDTO(name="Maria Souza", username="msouza", email="m@example.com"),
    )

    assert (response.name, response.username, response.email) == ("Maria Souza", "msouza", "m@example.com")
    assert uow.committed is True


def test_update_user_keeps_role_family_password_and_status(user_service, uow, actor):
    user = make_user(uow, Role.FAMILY_ADMIN)
    family_id, hashed = user.family_id, user.password_hash

    user_service.update_user(actor, user.id, UpdateUserDTO(name="Outra", username="outra", email=user.email))

    stored = uow.users.get_by_id(user.id)
    assert (stored.role, stored.family_id, stored.password_hash, stored.status) == (
        Role.FAMILY_ADMIN, family_id, hashed, AccountStatus.ACTIVE
    )


def test_update_user_keeping_own_username_and_email_is_allowed(user_service, uow, actor):
    user = make_user(uow, username="maria", email="maria@example.com")

    response = user_service.update_user(
        actor, user.id, UpdateUserDTO(name="Novo", username="MARIA", email="Maria@Example.com"),
    )

    assert response.name == "Novo"


def test_update_user_to_another_users_username_raises(user_service, uow, actor):
    make_user(uow, username="joao", email="joao@example.com")
    other = make_user(uow, username="maria", email="maria@example.com")

    with pytest.raises(EntityAlreadyExistsError) as exc:
        user_service.update_user(actor, other.id, UpdateUserDTO(name="Maria", username="JOAO", email=other.email))

    assert exc.value.field == "username"


def test_update_pending_user_to_another_users_email_raises(user_service, uow, actor):
    make_user(uow, username="joao", email="joao@example.com")
    other = make_user(uow, username="maria", email="maria@example.com", activated=False)

    with pytest.raises(EntityAlreadyExistsError) as exc:
        user_service.update_user(actor, other.id, UpdateUserDTO(name="Maria", username="maria", email="JOAO@example.com"))

    assert exc.value.field == "email"


def test_update_user_with_blank_name_raises_and_keeps_current_data(user_service, uow, actor):
    user = make_user(uow, name="Maria", username="maria", email="maria@example.com")

    with pytest.raises(DomainValidationError, match="Nome é obrigatório"):
        user_service.update_user(actor, user.id, UpdateUserDTO(name="  ", username="outro", email=user.email))

    stored = uow.users.get_by_id(user.id)
    assert (stored.name, stored.username) == ("Maria", "maria")
    assert uow.committed is False


def test_update_user_not_found(user_service, actor):
    with pytest.raises(EntityNotFoundError):
        user_service.update_user(actor, uuid.uuid4(), UpdateUserDTO(name="X", username="x", email="x@example.com"))


# --- E-mail: trava depois da ativação (nenhum administrador o altera) ---

def test_administrator_can_correct_the_email_before_activation(user_service, uow, actor):
    user = make_user(uow, activated=False, email="errado@example.com")

    response = user_service.update_user(actor, user.id, UpdateUserDTO(name=user.name, username=user.username, email="certo@example.com"))

    assert response.email == "certo@example.com"


@pytest.mark.parametrize("admin_role", [Role.SYSTEM_ADMIN, Role.FAMILY_ADMIN])
def test_nobody_changes_the_email_of_an_activated_account(user_service, uow, family, admin_role):
    admin = make_user(uow, admin_role, family=family if admin_role is Role.FAMILY_ADMIN else None)
    target = make_user(uow, Role.FAMILY_USER, family=family, email="original@example.com")

    with pytest.raises(DomainValidationError, match="depois que a conta foi ativada") as exc:
        user_service.update_user(
            principal_of(admin), target.id, UpdateUserDTO(name=target.name, username=target.username, email="invasor@example.com"),
        )

    assert exc.value.field == "email"
    assert uow.users.get_by_id(target.id).email == "original@example.com"
    assert uow.committed is False


def test_the_email_lock_does_not_block_other_edits_of_an_activated_account(user_service, uow, actor):
    target = make_user(uow, Role.FAMILY_USER, name="Antigo", email="original@example.com")

    response = user_service.update_user(
        actor, target.id, UpdateUserDTO(name="Novo Nome", username="novo.usuario", email="original@example.com"),
    )

    assert (response.name, response.username, response.email) == ("Novo Nome", "novo.usuario", "original@example.com")


def test_email_lock_holds_while_the_account_awaits_a_new_password(user_service, uow):
    admin_a = make_user(uow, Role.SYSTEM_ADMIN)
    admin_b = make_user(uow, Role.SYSTEM_ADMIN, email="b@example.com")
    user_service.issue_invitation(principal_of(admin_a), admin_b.id)       # revoga a senha de admin_b
    assert uow.users.get_by_id(admin_b.id).status is AccountStatus.AWAITING_PASSWORD

    with pytest.raises(DomainValidationError, match="depois que a conta foi ativada"):
        user_service.update_user(
            principal_of(admin_a), admin_b.id, UpdateUserDTO(name=admin_b.name, username=admin_b.username, email="roubo@example.com"),
        )


# ---------------------------------------------------------------------------
# Desativar e reativar
# ---------------------------------------------------------------------------

def test_deactivate_and_reactivate_user(user_service, uow, actor):
    user = make_user(uow)

    deactivated = user_service.deactivate_user(actor, user.id)
    assert (deactivated.is_active, deactivated.status) == (False, AccountStatus.DEACTIVATED)
    assert uow.users.get_by_id(user.id).can_authenticate is False

    reactivated = user_service.reactivate_user(actor, user.id)
    assert (reactivated.is_active, reactivated.status) == (True, AccountStatus.ACTIVE)
    assert uow.users.get_by_id(user.id).can_authenticate is True


def test_deactivation_keeps_the_data(user_service, uow, actor):
    user = make_user(uow, name="Maria", username="maria")
    user_service.deactivate_user(actor, user.id)

    stored = uow.users.get_by_id(user.id)
    assert (stored.name, stored.username, stored.password_hash) == ("Maria", "maria", user.password_hash)


def test_nobody_deactivates_their_own_account(user_service, sysadmin, actor):
    with pytest.raises(DomainValidationError, match="não pode desativar a sua própria conta"):
        user_service.deactivate_user(actor, sysadmin.id)
    assert sysadmin.is_active is True


def test_deactivation_of_a_missing_user_is_not_found(user_service, actor):
    with pytest.raises(EntityNotFoundError):
        user_service.deactivate_user(actor, uuid.uuid4())


# ---------------------------------------------------------------------------
# Convite: reenviar ativação e redefinir a senha de um administrador do sistema
# ---------------------------------------------------------------------------

def test_reissue_for_a_pending_account_sends_a_new_activation_and_revokes_the_old_link(
    user_service, uow, emails, actor,
):
    first = user_service.create_user(actor, _dto(role=Role.FAMILY_USER, family_id=make_family(uow).id))
    first_token = token_from_link(emails.last["body"])
    first_invitation = uow.invitations.get_active_for_user(first.user.id)

    second = user_service.issue_invitation(actor, first.user.id)

    assert second.purpose is InvitationPurpose.ACTIVATION
    assert second.code != first.code
    assert first_invitation.revoked_at is not None                         # o convite antigo morreu
    new_invitation = uow.invitations.get_active_for_user(first.user.id)
    assert new_invitation.id != first_invitation.id
    assert token_from_link(emails.last["body"]) != first_token
    assert len([i for i in uow.invitations.invitations.values() if i.revoked_at is None and i.consumed_at is None]) == 1


def test_reissue_reports_when_the_email_could_not_be_sent(user_service, uow, emails, actor):
    pending = make_user(uow, activated=False)
    emails.fail = True

    issued = user_service.issue_invitation(actor, pending.id)

    assert issued.email_sent is False
    assert uow.invitations.get_active_for_user(pending.id) is not None


def test_system_admin_resets_another_system_admins_password_with_link_and_code(user_service, uow, emails, actor):
    peer = make_user(uow, Role.SYSTEM_ADMIN, username="peer")
    old_hash = peer.password_hash

    issued = user_service.issue_invitation(actor, peer.id)

    assert issued.purpose is InvitationPurpose.ADMIN_RESET
    stored = uow.users.get_by_id(peer.id)
    assert stored.password_hash is None and stored.password_hash != old_hash     # a senha antiga já não vale
    assert stored.status is AccountStatus.AWAITING_PASSWORD
    assert stored.can_authenticate is False
    assert uow.invitations.get_active_for_user(peer.id).requires_code is True
    assert issued.code
    assert "redefinição" in emails.last["subject"].lower()
    assert normalize_code(issued.code) not in emails.last["body"]


def test_root_can_reset_a_system_admins_password(user_service, uow):
    root = make_user(uow, Role.ROOT, username="root")
    admin = make_user(uow, Role.SYSTEM_ADMIN, username="admin")

    issued = user_service.issue_invitation(principal_of(root), admin.id)

    assert issued.purpose is InvitationPurpose.ADMIN_RESET


def test_family_users_who_already_activated_reset_their_own_password(user_service, uow, family, actor):
    """Decidido: usuário de família e administrador de família já ativados redefinem a senha sozinhos."""
    for role in (Role.FAMILY_USER, Role.FAMILY_ADMIN):
        target = make_user(uow, role, family=family)
        with pytest.raises(DomainValidationError, match="redefinem a senha por conta própria"):
            user_service.issue_invitation(actor, target.id)
        assert uow.users.get_by_id(target.id).password_hash == target.password_hash       # nada foi revogado
        assert uow.invitations.get_active_for_user(target.id) is None


def test_family_admin_reissues_the_activation_of_a_pending_user_of_its_own_family(user_service, uow, family):
    family_admin = make_user(uow, Role.FAMILY_ADMIN, family=family)
    pending = make_user(uow, Role.FAMILY_USER, family=family, activated=False)

    issued = user_service.issue_invitation(principal_of(family_admin), pending.id)

    assert issued.purpose is InvitationPurpose.ACTIVATION


def test_nobody_issues_an_invitation_for_themselves(user_service, sysadmin, actor):
    with pytest.raises(AccessDeniedError):
        user_service.issue_invitation(actor, sysadmin.id)


def test_nobody_issues_an_invitation_for_a_deactivated_account(user_service, uow, actor):
    target = make_user(uow, activated=False, active=False)
    with pytest.raises(DomainValidationError, match="desativada"):
        user_service.issue_invitation(actor, target.id)


def test_issue_invitation_for_a_missing_user_is_not_found(user_service, actor):
    with pytest.raises(EntityNotFoundError):
        user_service.issue_invitation(actor, uuid.uuid4())


def test_the_root_account_never_gets_an_invitation(user_service, uow, actor):
    root = make_user(uow, Role.ROOT, username="root")
    with pytest.raises(AccessDeniedError):
        user_service.issue_invitation(actor, root.id)
    assert uow.users.get_by_id(root.id).password_hash == root.password_hash


# ---------------------------------------------------------------------------
# Exclusão
# ---------------------------------------------------------------------------

def test_delete_user_success(user_service, uow, actor):
    user = make_user(uow)

    user_service.delete_user(actor, user.id)

    assert uow.users.get_by_id(user.id) is None
    assert uow.committed is True


def test_delete_user_removes_its_invitations(user_service, uow, actor):
    pending = make_user(uow, activated=False)
    user_service.issue_invitation(actor, pending.id)
    assert uow.invitations.get_active_for_user(pending.id) is not None

    user_service.delete_user(actor, pending.id)

    assert uow.invitations.get_active_for_user(pending.id) is None
    assert all(i.user_id != pending.id for i in uow.invitations.invitations.values())


def test_delete_user_with_dependencies_raises_and_keeps_user(user_service, uow, actor):
    user = make_user(uow)
    uow.users.set_has_dependencies(True)

    with pytest.raises(EntityHasDependenciesError):
        user_service.delete_user(actor, user.id)

    assert uow.users.get_by_id(user.id) is not None


def test_delete_root_is_blocked_with_an_explanation(user_service, uow, actor):
    root = make_user(uow, Role.ROOT, username="root")

    with pytest.raises(EntityHasDependenciesError, match="usuário root"):
        user_service.delete_user(actor, root.id)

    assert uow.users.get_by_id(root.id) is not None


def test_nobody_deletes_their_own_account(user_service, sysadmin, actor):
    with pytest.raises(DomainValidationError, match="não pode excluir a sua própria conta"):
        user_service.delete_user(actor, sysadmin.id)


def test_delete_user_not_found(user_service, actor):
    with pytest.raises(EntityNotFoundError):
        user_service.delete_user(actor, uuid.uuid4())


def test_preview_user_deletion_without_dependencies(user_service, uow, actor):
    user = make_user(uow, name="Maria")

    preview = user_service.preview_user_deletion(actor, user.id)

    assert (preview.name, preview.blocked_reason) == ("Maria", None)


def test_preview_user_deletion_with_dependencies_gives_the_reason(user_service, uow, actor):
    user = make_user(uow)
    uow.users.set_has_dependencies(True)

    preview = user_service.preview_user_deletion(actor, user.id)

    assert preview.blocked_reason == str(user_has_dependencies(user.id))


def test_preview_root_deletion_is_blocked_and_named_by_username(user_service, uow, actor):
    root = make_user(uow, Role.ROOT, username="root")

    preview = user_service.preview_user_deletion(actor, root.id)

    assert preview.name == "root"
    assert "usuário root" in preview.blocked_reason


def test_preview_of_own_account_explains_why_it_is_blocked(user_service, sysadmin, actor):
    preview = user_service.preview_user_deletion(actor, sysadmin.id)
    assert "própria conta" in preview.blocked_reason


def test_preview_user_deletion_not_found(user_service, actor):
    with pytest.raises(EntityNotFoundError):
        user_service.preview_user_deletion(actor, uuid.uuid4())

