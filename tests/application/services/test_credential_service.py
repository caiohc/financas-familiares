"""
Definir a senha por convite (ativação e redefinição de administrador do sistema: link + código) e recuperação
autônoma ("Esqueci minha senha": só o link). Inclui o que um atacante tentaria: código errado em série,
convite vencido, reutilizado, trocado de finalidade, revogado, ou o link de outra pessoa.
"""
from datetime import timedelta

import pytest

from application.services.credential_service import SET_PASSWORD_PURPOSES
from domain.identity.entities import AccountStatus, Role
from domain.identity.invitations import InvitationPurpose, normalize_code
from domain.shared.exceptions import AuthenticationFailedError, DomainValidationError
from fakes.identity_builders import PASSWORD, hashed, make_family, make_user, principal_of
from fakes.identity_fakes import token_from_link
from application.dtos.identity_dtos import CreateUserDTO

NEW_PASSWORD = "minha-nova-senha-789"
INVALID_INVITATION = "Convite ou código inválido, expirado ou já utilizado."
INVALID_LINK = "Link inválido, expirado ou já utilizado."


@pytest.fixture
def admin(uow):
    return make_user(uow, Role.SYSTEM_ADMIN, username="admin")


@pytest.fixture
def invited(user_service, uow, emails, admin):
    """Um usuário de família recém-cadastrado: conta pendente, com convite de ativação."""
    family = make_family(uow)
    issued = user_service.create_user(principal_of(admin), CreateUserDTO(
        role=Role.FAMILY_USER, family_id=family.id, name="Maria", username="maria", email="maria@example.com",
        email_confirmation="maria@example.com",
    ))
    return {"user": uow.users.get_by_id(issued.user.id), "code": issued.code, "token": token_from_link(emails.last["body"])}


def _activate(credential_service, invited, **overrides):
    data = dict(code=invited["code"], password=NEW_PASSWORD, password_confirmation=NEW_PASSWORD)
    data.update(overrides)
    return credential_service.complete_invitation(overrides.pop("token", invited["token"]), data["code"], data["password"], data["password_confirmation"])


# ---------------------------------------------------------------------------
# Página do link
# ---------------------------------------------------------------------------

def test_inspect_invitation_tells_only_what_the_page_needs(credential_service, invited):
    info = credential_service.inspect_invitation(invited["token"], SET_PASSWORD_PURPOSES)

    assert info.purpose is InvitationPurpose.ACTIVATION and info.requires_code is True
    assert not hasattr(info, "user") and not hasattr(info, "email")


@pytest.mark.parametrize("token", [None, "", "token-inexistente", "A" * 43, " ", "../../etc/passwd"])
def test_inspect_invitation_with_an_unknown_token_fails_generically(credential_service, token):
    with pytest.raises(AuthenticationFailedError) as exc:
        credential_service.inspect_invitation(token, SET_PASSWORD_PURPOSES)
    assert str(exc.value) == INVALID_INVITATION


# ---------------------------------------------------------------------------
# Ativação: token + código + senha definida pela própria pessoa
# ---------------------------------------------------------------------------

def test_activation_sets_the_password_chosen_by_the_user_and_activates_the_account(credential_service, uow, invited):
    _activate(credential_service, invited)

    user = uow.users.get_by_id(invited["user"].id)
    assert user.password_hash == hashed(NEW_PASSWORD)
    assert user.status is AccountStatus.ACTIVE and user.activated_at is not None
    assert uow.committed is True


def test_after_activation_the_user_can_log_in_and_the_email_is_trusted(credential_service, auth_service, invited):
    _activate(credential_service, invited)

    assert auth_service.authenticate("maria", NEW_PASSWORD).role is Role.FAMILY_USER


def test_the_code_is_accepted_however_the_person_types_it(credential_service, invited):
    typed = invited["code"].lower().replace("-", " ")
    _activate(credential_service, invited, code=typed)


def test_the_invitation_is_single_use(credential_service, uow, invited):
    _activate(credential_service, invited)

    with pytest.raises(AuthenticationFailedError):
        _activate(credential_service, invited, password="outra-senha-1234", password_confirmation="outra-senha-1234")
    assert uow.users.get_by_id(invited["user"].id).password_hash == hashed(NEW_PASSWORD)


def test_a_wrong_code_fails_with_the_generic_message_and_does_not_activate(credential_service, uow, invited):
    with pytest.raises(AuthenticationFailedError) as exc:
        _activate(credential_service, invited, code="ZZZZ-ZZZZ")

    assert str(exc.value) == INVALID_INVITATION
    assert uow.users.get_by_id(invited["user"].id).is_pending


@pytest.mark.parametrize("code", [None, "", "   ", "----", "ABCD", "ABCD-EFGH-IJKL"])
def test_missing_or_malformed_codes_fail_like_a_wrong_code(credential_service, uow, invited, code):
    with pytest.raises(AuthenticationFailedError):
        _activate(credential_service, invited, code=code)

    assert uow.users.get_by_id(invited["user"].id).is_pending
    assert uow.invitations.get_active_for_user(invited["user"].id).attempts == 1


def test_every_wrong_code_counts_one_attempt(credential_service, uow, invited):
    for expected in (1, 2, 3):
        with pytest.raises(AuthenticationFailedError):
            _activate(credential_service, invited, code="ZZZZ-ZZZZ")
        assert uow.invitations.get_active_for_user(invited["user"].id).attempts == expected


def test_the_failed_attempt_is_committed_even_though_the_request_fails(credential_service, uow, invited):
    uow.committed = False

    with pytest.raises(AuthenticationFailedError):
        _activate(credential_service, invited, code="ZZZZ-ZZZZ")

    assert uow.committed is True           # sem o commit, o rollback da falha apagaria a tentativa


def test_after_five_wrong_codes_even_the_right_code_stops_working(credential_service, uow, invited, settings):
    for _ in range(settings.max_code_attempts):
        with pytest.raises(AuthenticationFailedError):
            _activate(credential_service, invited, code="ZZZZ-ZZZZ")

    with pytest.raises(AuthenticationFailedError) as exc:
        _activate(credential_service, invited)                         # o código CERTO, agora recusado

    assert str(exc.value) == INVALID_INVITATION
    assert uow.users.get_by_id(invited["user"].id).is_pending
    assert uow.invitations.get_active_for_user(invited["user"].id).attempts == 5     # não passa do limite


def test_four_wrong_codes_still_leave_the_right_one_working(credential_service, uow, invited):
    for _ in range(4):
        with pytest.raises(AuthenticationFailedError):
            _activate(credential_service, invited, code="ZZZZ-ZZZZ")

    _activate(credential_service, invited)

    assert uow.users.get_by_id(invited["user"].id).status is AccountStatus.ACTIVE


def test_a_locked_invitation_is_recovered_only_by_issuing_a_new_one(credential_service, user_service, uow, emails, admin, invited, settings):
    for _ in range(settings.max_code_attempts):
        with pytest.raises(AuthenticationFailedError):
            _activate(credential_service, invited, code="ZZZZ-ZZZZ")

    new = user_service.issue_invitation(principal_of(admin), invited["user"].id)
    new_token = token_from_link(emails.last["body"])
    credential_service.complete_invitation(new_token, new.code, NEW_PASSWORD, NEW_PASSWORD)

    assert uow.users.get_by_id(invited["user"].id).status is AccountStatus.ACTIVE


def test_the_old_link_and_code_die_when_a_new_invitation_is_issued(credential_service, user_service, uow, emails, admin, invited):
    new = user_service.issue_invitation(principal_of(admin), invited["user"].id)
    new_token = token_from_link(emails.last["body"])

    with pytest.raises(AuthenticationFailedError):
        _activate(credential_service, invited)                                     # link e código antigos
    with pytest.raises(AuthenticationFailedError):
        credential_service.complete_invitation(invited["token"], new.code, NEW_PASSWORD, NEW_PASSWORD)   # link antigo, código novo
    with pytest.raises(AuthenticationFailedError):
        credential_service.complete_invitation(new_token, invited["code"], NEW_PASSWORD, NEW_PASSWORD)   # link novo, código antigo
    assert uow.users.get_by_id(invited["user"].id).is_pending


def test_the_token_alone_is_not_enough(credential_service, uow, invited):
    for code in (None, "", "AAAA-AAAA"):
        with pytest.raises(AuthenticationFailedError):
            _activate(credential_service, invited, code=code)
    assert uow.users.get_by_id(invited["user"].id).is_pending


def test_the_code_alone_is_not_enough(credential_service, uow, invited):
    for token in (None, "", "token-qualquer", invited["token"][:-1], invited["token"] + "x", invited["token"].swapcase()):
        with pytest.raises(AuthenticationFailedError):
            credential_service.complete_invitation(token, invited["code"], NEW_PASSWORD, NEW_PASSWORD)
    assert uow.users.get_by_id(invited["user"].id).is_pending


def test_the_code_of_one_invitation_does_not_open_another_persons_link(credential_service, user_service, uow, emails, admin, invited):
    other_family = make_family(uow)
    other = user_service.create_user(principal_of(admin), CreateUserDTO(
        role=Role.FAMILY_USER, family_id=other_family.id, name="Outra", username="outra", email="outra@example.com",
        email_confirmation="outra@example.com",
    ))
    other_token = token_from_link(emails.last["body"])

    with pytest.raises(AuthenticationFailedError):
        credential_service.complete_invitation(other_token, invited["code"], NEW_PASSWORD, NEW_PASSWORD)   # código do Maria no link da Outra

    assert uow.users.get_by_id(other.user.id).is_pending and uow.users.get_by_id(invited["user"].id).is_pending


# --- Validade (24 horas) ---

def test_the_invitation_works_until_the_deadline_and_not_after(credential_service, uow, clock, invited):
    clock.advance(hours=23, minutes=59)
    credential_service.inspect_invitation(invited["token"], SET_PASSWORD_PURPOSES)

    clock.advance(minutes=1)
    with pytest.raises(AuthenticationFailedError):
        credential_service.inspect_invitation(invited["token"], SET_PASSWORD_PURPOSES)
    with pytest.raises(AuthenticationFailedError):
        _activate(credential_service, invited)
    assert uow.users.get_by_id(invited["user"].id).is_pending


def test_an_expired_invitation_does_not_even_count_attempts(credential_service, uow, clock, invited):
    clock.advance(hours=25)
    with pytest.raises(AuthenticationFailedError):
        _activate(credential_service, invited, code="ZZZZ-ZZZZ")
    assert uow.invitations.get_active_for_user(invited["user"].id).attempts == 0


# --- Senha inválida não gasta tentativa nem o convite ---

@pytest.mark.parametrize("password, confirmation, message", [
    ("curta", "curta", "pelo menos 8 caracteres"),
    ("", "", "Senha é obrigatória"),
    (None, None, "Senha é obrigatória"),
    (NEW_PASSWORD, "outra-coisa-1234", "senhas informadas não conferem"),
    (NEW_PASSWORD, None, "senhas informadas não conferem"),
])
def test_a_bad_password_is_a_validation_error_that_keeps_the_invitation_usable(credential_service, uow, invited, password, confirmation, message):
    with pytest.raises(DomainValidationError, match=message):
        _activate(credential_service, invited, password=password, password_confirmation=confirmation)

    invitation = uow.invitations.get_active_for_user(invited["user"].id)
    assert invitation.attempts == 0 and invitation.consumed_at is None
    _activate(credential_service, invited)                              # ainda dá para ativar


def test_a_bad_password_with_a_wrong_code_still_reveals_nothing_about_the_code(credential_service, invited):
    with pytest.raises(DomainValidationError):
        _activate(credential_service, invited, code="ZZZZ-ZZZZ", password="curta", password_confirmation="curta")


# --- Conta desativada ou excluída ---

def test_a_deactivated_account_cannot_be_activated_by_an_old_invitation(credential_service, uow, invited):
    uow.users.get_by_id(invited["user"].id).deactivate()

    with pytest.raises(AuthenticationFailedError):
        _activate(credential_service, invited)
    with pytest.raises(AuthenticationFailedError):
        credential_service.inspect_invitation(invited["token"], SET_PASSWORD_PURPOSES)


def test_a_deleted_account_leaves_a_dead_link(credential_service, uow, invited):
    uow.users.delete(invited["user"].id)

    with pytest.raises(AuthenticationFailedError):
        _activate(credential_service, invited)


# --- Finalidade: cada link só vale na sua página ---

def test_a_recovery_token_cannot_be_used_as_an_activation_link(credential_service, uow, emails):
    family_user = make_user(uow, Role.FAMILY_USER, email="rec@example.com")
    credential_service.request_recovery("rec@example.com")
    recovery_token = token_from_link(emails.last["body"])

    with pytest.raises(AuthenticationFailedError):
        credential_service.inspect_invitation(recovery_token, SET_PASSWORD_PURPOSES)
    with pytest.raises(AuthenticationFailedError):
        credential_service.complete_invitation(recovery_token, "ABCD-EFGH", NEW_PASSWORD, NEW_PASSWORD)
    assert uow.users.get_by_id(family_user.id).password_hash == family_user.password_hash


def test_an_activation_token_cannot_be_used_as_a_recovery_link(credential_service, uow, invited):
    with pytest.raises(AuthenticationFailedError) as exc:
        credential_service.inspect_recovery(invited["token"])
    assert str(exc.value) == INVALID_LINK
    with pytest.raises(AuthenticationFailedError):
        credential_service.complete_recovery(invited["token"], NEW_PASSWORD, NEW_PASSWORD)
    assert uow.users.get_by_id(invited["user"].id).is_pending


# ---------------------------------------------------------------------------
# Redefinição de administrador do sistema (link + código)
# ---------------------------------------------------------------------------

@pytest.fixture
def reset(user_service, uow, emails, admin):
    peer = make_user(uow, Role.SYSTEM_ADMIN, username="peer", password="senha-antiga-123")
    issued = user_service.issue_invitation(principal_of(admin), peer.id)
    return {"user": peer, "code": issued.code, "token": token_from_link(emails.last["body"])}


def test_admin_reset_sets_a_new_password_with_token_and_code(credential_service, uow, reset):
    credential_service.complete_invitation(reset["token"], reset["code"], NEW_PASSWORD, NEW_PASSWORD)

    user = uow.users.get_by_id(reset["user"].id)
    assert user.password_hash == hashed(NEW_PASSWORD) and user.status is AccountStatus.ACTIVE


def test_the_old_password_is_dead_from_the_moment_the_reset_is_issued(auth_service, reset):
    from domain.shared.exceptions import AuthenticationFailedError as Failed

    with pytest.raises(Failed):
        auth_service.authenticate("peer", "senha-antiga-123")


def test_admin_reset_notifies_the_user_that_the_password_changed(credential_service, emails, reset):
    emails.outbox.clear()

    credential_service.complete_invitation(reset["token"], reset["code"], NEW_PASSWORD, NEW_PASSWORD)

    assert emails.last["to"] == reset["user"].email and "alterada" in emails.last["subject"].lower()


def test_activation_does_not_send_a_password_changed_notice(credential_service, emails, invited):
    emails.outbox.clear()
    _activate(credential_service, invited)
    assert emails.outbox == []


def test_admin_reset_is_also_protected_by_the_attempt_limit(credential_service, uow, reset, settings):
    for _ in range(settings.max_code_attempts):
        with pytest.raises(AuthenticationFailedError):
            credential_service.complete_invitation(reset["token"], "ZZZZ-ZZZZ", NEW_PASSWORD, NEW_PASSWORD)

    with pytest.raises(AuthenticationFailedError):
        credential_service.complete_invitation(reset["token"], reset["code"], NEW_PASSWORD, NEW_PASSWORD)
    assert uow.users.get_by_id(reset["user"].id).status is AccountStatus.AWAITING_PASSWORD


def test_the_reset_keeps_the_original_activation_date(credential_service, uow, reset):
    activated = reset["user"].activated_at
    credential_service.complete_invitation(reset["token"], reset["code"], NEW_PASSWORD, NEW_PASSWORD)
    assert uow.users.get_by_id(reset["user"].id).activated_at == activated


# ---------------------------------------------------------------------------
# Recuperação autônoma ("Esqueci minha senha"): só o link, 15 minutos
# ---------------------------------------------------------------------------

@pytest.fixture
def family_account(uow):
    return make_user(uow, Role.FAMILY_ADMIN, username="ana", email="ana@example.com", password=PASSWORD)


@pytest.mark.parametrize("role", [Role.FAMILY_ADMIN, Role.FAMILY_USER])
def test_recovery_sends_a_link_to_an_activated_family_account(credential_service, uow, emails, role):
    make_user(uow, role, username="u", email="u@example.com")

    credential_service.request_recovery("u@example.com")

    assert len(emails.outbox) == 1
    assert emails.last["to"] == "u@example.com"
    assert "https://app.test/auth/recover/" in emails.last["body"]
    assert "CÓDIGO" not in emails.last["body"]                    # recuperação não usa código


def test_recovery_ignores_case_and_spaces_in_the_email(credential_service, family_account, emails):
    credential_service.request_recovery("  ANA@Example.COM ")
    assert len(emails.outbox) == 1


@pytest.fixture
def silent_cases(uow):
    """Contas para as quais a recuperação NÃO pode enviar nada (e o pedido tem de parecer igual)."""
    make_user(uow, Role.FAMILY_USER, username="pendente", email="pendente@example.com", activated=False)
    make_user(uow, Role.FAMILY_USER, username="desativado", email="desativado@example.com", active=False)
    make_user(uow, Role.SYSTEM_ADMIN, username="sysadmin", email="sysadmin@example.com")
    make_user(uow, Role.ROOT, username="root", email="root@example.com")
    awaiting = make_user(uow, Role.SYSTEM_ADMIN, username="aguardando", email="aguardando@example.com")
    awaiting.revoke_password()
    return ["pendente@example.com", "desativado@example.com", "sysadmin@example.com", "root@example.com",
            "aguardando@example.com", "ninguem@example.com", "", None, "nao-e-email", "  "]


def test_recovery_sends_nothing_and_changes_nothing_for_ineligible_requests(credential_service, uow, emails, silent_cases):
    for email in silent_cases:
        credential_service.request_recovery(email)         # nunca levanta: a resposta é sempre a mesma

    assert emails.outbox == []
    assert uow.invitations.invitations == {}


def test_recovery_response_is_the_same_whether_or_not_the_account_exists(credential_service, family_account):
    assert credential_service.request_recovery("ana@example.com") is None
    assert credential_service.request_recovery("ninguem@example.com") is None


def test_system_admin_and_root_are_never_recoverable_by_email(credential_service, uow, emails):
    make_user(uow, Role.SYSTEM_ADMIN, username="adm", email="adm@example.com")
    make_user(uow, Role.ROOT, username="root", email="root@example.com")

    credential_service.request_recovery("adm@example.com")
    credential_service.request_recovery("root@example.com")

    assert emails.outbox == []


def test_recovery_issues_one_active_link_per_user_and_revokes_the_previous(credential_service, uow, emails, family_account):
    credential_service.request_recovery("ana@example.com")
    first = token_from_link(emails.last["body"])
    credential_service.request_recovery("ana@example.com")
    second = token_from_link(emails.last["body"])

    assert first != second
    with pytest.raises(AuthenticationFailedError):
        credential_service.inspect_recovery(first)
    credential_service.inspect_recovery(second)


def test_recovery_completes_with_a_password_chosen_by_the_user(credential_service, auth_service, uow, emails, family_account):
    credential_service.request_recovery("ana@example.com")
    token = token_from_link(emails.last["body"])

    credential_service.complete_recovery(token, NEW_PASSWORD, NEW_PASSWORD)

    assert auth_service.authenticate("ana", NEW_PASSWORD)
    with pytest.raises(AuthenticationFailedError):
        auth_service.authenticate("ana", PASSWORD)


def test_recovery_link_is_single_use(credential_service, uow, emails, family_account):
    credential_service.request_recovery("ana@example.com")
    token = token_from_link(emails.last["body"])
    credential_service.complete_recovery(token, NEW_PASSWORD, NEW_PASSWORD)

    with pytest.raises(AuthenticationFailedError):
        credential_service.complete_recovery(token, "outra-senha-4567", "outra-senha-4567")
    with pytest.raises(AuthenticationFailedError):
        credential_service.inspect_recovery(token)
    assert uow.users.get_by_id(family_account.id).password_hash == hashed(NEW_PASSWORD)


def test_recovery_link_lasts_fifteen_minutes(credential_service, clock, emails, family_account):
    credential_service.request_recovery("ana@example.com")
    token = token_from_link(emails.last["body"])

    clock.advance(minutes=14, seconds=59)
    credential_service.inspect_recovery(token)

    clock.advance(seconds=1)
    with pytest.raises(AuthenticationFailedError) as exc:
        credential_service.inspect_recovery(token)
    assert str(exc.value) == INVALID_LINK
    with pytest.raises(AuthenticationFailedError):
        credential_service.complete_recovery(token, NEW_PASSWORD, NEW_PASSWORD)


def test_recovery_notifies_the_user_that_the_password_changed(credential_service, emails, family_account):
    credential_service.request_recovery("ana@example.com")
    token = token_from_link(emails.last["body"])
    emails.outbox.clear()

    credential_service.complete_recovery(token, NEW_PASSWORD, NEW_PASSWORD)

    assert emails.last["to"] == "ana@example.com" and "alterada" in emails.last["subject"].lower()
    assert NEW_PASSWORD not in emails.last["body"]


def test_recovery_kills_every_old_session(credential_service, auth_service, emails, family_account):
    old_session = auth_service.authenticate("ana", PASSWORD).session_id
    credential_service.request_recovery("ana@example.com")
    credential_service.complete_recovery(token_from_link(emails.last["body"]), NEW_PASSWORD, NEW_PASSWORD)

    assert auth_service.load_session_user(old_session) is None


@pytest.mark.parametrize("password, confirmation, message", [
    ("curta", "curta", "pelo menos 8 caracteres"),
    (NEW_PASSWORD, "diferente-1234567", "senhas informadas não conferem"),
    (None, None, "Senha é obrigatória"),
])
def test_recovery_with_a_bad_password_keeps_the_link_usable(credential_service, uow, emails, family_account, password, confirmation, message):
    credential_service.request_recovery("ana@example.com")
    token = token_from_link(emails.last["body"])

    with pytest.raises(DomainValidationError, match=message):
        credential_service.complete_recovery(token, password, confirmation)

    assert uow.users.get_by_id(family_account.id).password_hash == family_account.password_hash
    credential_service.complete_recovery(token, NEW_PASSWORD, NEW_PASSWORD)       # o link continua valendo


@pytest.mark.parametrize("token", [None, "", "inventado", "A" * 43])
def test_recovery_with_an_unknown_token_fails_generically(credential_service, token):
    with pytest.raises(AuthenticationFailedError) as exc:
        credential_service.complete_recovery(token, NEW_PASSWORD, NEW_PASSWORD)
    assert str(exc.value) == INVALID_LINK


def test_a_link_issued_before_deactivation_stops_working(credential_service, uow, emails, family_account):
    credential_service.request_recovery("ana@example.com")
    token = token_from_link(emails.last["body"])
    uow.users.get_by_id(family_account.id).deactivate()

    with pytest.raises(AuthenticationFailedError):
        credential_service.complete_recovery(token, NEW_PASSWORD, NEW_PASSWORD)


def test_a_link_issued_to_a_family_account_stops_working_if_the_account_is_deleted(credential_service, uow, emails, family_account):
    credential_service.request_recovery("ana@example.com")
    token = token_from_link(emails.last["body"])
    uow.users.delete(family_account.id)

    with pytest.raises(AuthenticationFailedError):
        credential_service.inspect_recovery(token)


def test_recovery_survives_a_failure_to_send_the_email(credential_service, emails, family_account):
    emails.fail = True
    credential_service.request_recovery("ana@example.com")             # não levanta: a resposta continua igual


def test_the_recovery_token_is_stored_only_as_a_hash(credential_service, uow, emails, family_account):
    credential_service.request_recovery("ana@example.com")
    token = token_from_link(emails.last["body"])

    invitation = uow.invitations.get_active_for_user(family_account.id)
    assert invitation.token_hash != token and token not in invitation.token_hash
    assert invitation.code_hash is None
    assert invitation.purpose is InvitationPurpose.RECOVERY
    assert invitation.expires_at - invitation.created_at == timedelta(minutes=15)
    assert normalize_code("") == ""
