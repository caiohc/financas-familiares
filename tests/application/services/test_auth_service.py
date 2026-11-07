"""Login, sessão e troca da própria senha. Inclui as tentativas de enumerar usuários e de reaproveitar sessões."""
import uuid

import pytest

from application.services.auth_service import AuthService
from domain.identity.entities import Role
from domain.shared.exceptions import AuthenticationFailedError, DomainValidationError, EntityNotFoundError
from fakes.identity_builders import PASSWORD, hashed, make_user
from fakes.identity_fakes import FakePasswordHasher

GENERIC = "Usuário ou senha inválidos."


@pytest.fixture
def account(uow):
    return make_user(uow, Role.FAMILY_USER, username="Maria", email="maria@example.com", password=PASSWORD)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("identifier", ["Maria", "maria", "MARIA", "  maria  ", "maria@example.com", "MARIA@EXAMPLE.COM"])
def test_login_by_username_or_email_ignoring_case(auth_service, account, identifier):
    dto = auth_service.authenticate(identifier, PASSWORD)

    assert dto.id == account.id
    assert dto.role is Role.FAMILY_USER


def test_login_result_exposes_no_password_material_besides_the_opaque_session_id(auth_service, account):
    dto = auth_service.authenticate("maria", PASSWORD)

    assert not hasattr(dto, "password_hash")
    assert account.password_hash not in repr(dto)
    assert PASSWORD not in repr(dto)


def test_password_is_compared_exactly_not_stripped(auth_service, uow):
    make_user(uow, username="espacos", password="  senha com espaços")
    assert auth_service.authenticate("espacos", "  senha com espaços")
    for variant in ("senha com espaços", "  senha com espaços ", "SENHA COM ESPAÇOS"):
        with pytest.raises(AuthenticationFailedError):
            auth_service.authenticate("espacos", variant)


# --- Toda falha tem a mesma resposta (não revela o que falhou) ---

@pytest.fixture
def failing_attempts(uow):
    """Cada tentativa que NÃO pode entrar, com o motivo real escondido por trás da mesma mensagem."""
    make_user(uow, username="ativa", password=PASSWORD)
    make_user(uow, username="pendente", activated=False)
    make_user(uow, username="desativada", password=PASSWORD, active=False)
    admin = make_user(uow, Role.SYSTEM_ADMIN, username="aguardando", password=PASSWORD)
    admin.revoke_password()
    return [
        ("ativa", "senha-errada-123"),            # senha errada
        ("ninguem", PASSWORD),                    # usuário inexistente
        ("pendente", PASSWORD),                   # conta ainda não ativada
        ("desativada", PASSWORD),                 # conta desativada (senha certa!)
        ("aguardando", PASSWORD),                 # senha revogada, aguardando nova
        ("ativa", ""),                            # senha vazia
        ("", PASSWORD),                           # identificador vazio
        (None, None),                             # nada
        ("ativa", None),
    ]


def test_every_kind_of_failure_gives_the_same_generic_message(auth_service, failing_attempts):
    for identifier, password in failing_attempts:
        with pytest.raises(AuthenticationFailedError) as exc:
            auth_service.authenticate(identifier, password)
        assert str(exc.value) == GENERIC, (identifier, password)


def test_a_failed_login_changes_nothing(auth_service, uow, failing_attempts):
    snapshot = {u.id: (u.password_hash, u.is_active, u.activated_at) for u in uow.users.users.values()}

    for identifier, password in failing_attempts:
        with pytest.raises(AuthenticationFailedError):
            auth_service.authenticate(identifier, password)

    assert {u.id: (u.password_hash, u.is_active, u.activated_at) for u in uow.users.users.values()} == snapshot
    assert uow.committed is False


@pytest.mark.parametrize("identifier", ["' OR '1'='1", "maria' --", "maria\"; DROP TABLE users;--", "%", "_", "*", "maria%"])
def test_injection_like_identifiers_simply_fail(auth_service, account, identifier):
    with pytest.raises(AuthenticationFailedError):
        auth_service.authenticate(identifier, PASSWORD)


def test_a_password_that_looks_like_a_hash_does_not_log_in(auth_service, account):
    with pytest.raises(AuthenticationFailedError):
        auth_service.authenticate("maria", account.password_hash)


# --- Tempo de resposta: sempre há uma conferência de senha ---

def test_an_unknown_user_still_costs_a_password_check_against_the_dummy_hash(auth_service, hasher):
    with pytest.raises(AuthenticationFailedError):
        auth_service.authenticate("ninguem", "qualquer-senha-123")

    assert len(hasher.verified) == 1
    assert hasher.verified[0] == ("qualquer-senha-123", hasher.dummy_hash())


def test_a_pending_account_also_costs_a_password_check(auth_service, uow, hasher):
    make_user(uow, username="pendente", activated=False)

    with pytest.raises(AuthenticationFailedError):
        auth_service.authenticate("pendente", "qualquer-senha-123")

    assert len(hasher.verified) == 1 and hasher.verified[0][1] == hasher.dummy_hash()


def test_the_password_is_checked_even_when_the_account_is_deactivated(auth_service, uow, hasher):
    make_user(uow, username="desativada", password=PASSWORD, active=False)

    with pytest.raises(AuthenticationFailedError):
        auth_service.authenticate("desativada", PASSWORD)

    assert len(hasher.verified) == 1


def test_the_dummy_hash_is_computed_once_and_is_never_a_real_users_hash(hasher, uow, account):
    first, second = hasher.dummy_hash(), hasher.dummy_hash()
    assert first == second
    assert first != account.password_hash


# --- Regravação do hash antigo ---

def test_login_rehashes_an_outdated_hash(auth_service, uow, hasher, account):
    hasher.outdated.add(account.password_hash)

    auth_service.authenticate("maria", PASSWORD)

    assert uow.users.get_by_id(account.id).password_hash == hashed(PASSWORD)
    assert uow.committed is True


def test_login_keeps_a_current_hash_untouched(auth_service, uow, account):
    auth_service.authenticate("maria", PASSWORD)
    assert uow.committed is False


def test_a_failed_login_never_rehashes(auth_service, uow, hasher, account):
    hasher.outdated.add(account.password_hash)
    with pytest.raises(AuthenticationFailedError):
        auth_service.authenticate("maria", "errada-errada-1")
    assert uow.committed is False


# ---------------------------------------------------------------------------
# Sessão: o cookie guarda "id:versão da credencial"
# ---------------------------------------------------------------------------

def test_session_id_carries_the_user_id_and_a_credential_version(auth_service, account):
    dto = auth_service.authenticate("maria", PASSWORD)

    user_id, _, version = dto.session_id.partition(":")
    assert user_id == str(account.id)
    assert len(version) == 32 and version != account.password_hash


def test_session_id_does_not_contain_the_password_hash(auth_service, account):
    dto = auth_service.authenticate("maria", PASSWORD)
    assert account.password_hash not in dto.session_id and PASSWORD not in dto.session_id


def test_the_session_loads_the_user_again_from_the_database(auth_service, uow, account):
    dto = auth_service.authenticate("maria", PASSWORD)
    account.name = "Nome Mudou"

    assert auth_service.load_session_user(dto.session_id).name == "Nome Mudou"


def test_changing_the_password_kills_every_old_session(auth_service, uow, account):
    old = auth_service.authenticate("maria", PASSWORD).session_id
    uow.users.get_by_id(account.id).change_password(hashed("outra-senha-1234"))

    assert auth_service.load_session_user(old) is None


def test_a_deactivated_user_loses_the_session_on_the_next_request(auth_service, uow, account):
    sid = auth_service.authenticate("maria", PASSWORD).session_id
    assert auth_service.load_session_user(sid) is not None

    uow.users.get_by_id(account.id).deactivate()

    assert auth_service.load_session_user(sid) is None


def test_a_deleted_user_loses_the_session(auth_service, uow, account):
    sid = auth_service.authenticate("maria", PASSWORD).session_id
    uow.users.delete(account.id)
    assert auth_service.load_session_user(sid) is None


def test_a_revoked_password_kills_the_session(auth_service, uow):
    admin = make_user(uow, Role.SYSTEM_ADMIN, username="admin")
    sid = auth_service.authenticate("admin", PASSWORD).session_id

    admin.revoke_password()

    assert auth_service.load_session_user(sid) is None


@pytest.mark.parametrize("bad", [None, "", "x", "sem-dois-pontos", ":", "não-é-uuid:abc", "::", "12345:abcdef"])
def test_garbage_session_ids_load_nobody(auth_service, bad):
    assert auth_service.load_session_user(bad) is None


def test_a_forged_version_does_not_load_the_user(auth_service, account):
    for forged in ("0" * 32, "", "a" * 32, account.password_hash):
        assert auth_service.load_session_user(f"{account.id}:{forged}") is None


def test_the_user_id_of_another_account_does_not_borrow_this_ones_version(auth_service, uow, account):
    other = make_user(uow, username="outro", password="outra-senha-1234")
    version = auth_service.authenticate("maria", PASSWORD).session_id.split(":")[1]

    assert auth_service.load_session_user(f"{other.id}:{version}") is None


def test_a_session_signed_with_another_secret_is_invalid(uow, hasher, access_manager, clock, account):
    mine = AuthService(uow, hasher, access_manager, "uma-chave", clock)
    theirs = AuthService(uow, hasher, access_manager, "outra-chave", clock)

    sid = mine.authenticate("maria", PASSWORD).session_id

    assert theirs.load_session_user(sid) is None


def test_a_unknown_user_id_loads_nobody(auth_service):
    assert auth_service.load_session_user(f"{uuid.uuid4()}:{'a' * 32}") is None


# --- Usuário de desenvolvimento (AUTH_ENABLED=false) ---

def test_dev_lookup_returns_only_users_that_could_log_in(auth_service, uow):
    make_user(uow, username="ok")
    make_user(uow, username="pendente", activated=False)
    make_user(uow, username="desativado", active=False)

    assert auth_service.find_session_user_by_username("ok") is not None
    assert auth_service.find_session_user_by_username("pendente") is None
    assert auth_service.find_session_user_by_username("desativado") is None
    assert auth_service.find_session_user_by_username("fantasma") is None
    assert auth_service.find_session_user_by_username("") is None


# ---------------------------------------------------------------------------
# Troca da própria senha
# ---------------------------------------------------------------------------

NEW_PASSWORD = "nova-senha-segura-456"


def test_change_own_password(auth_service, uow, account):
    dto = auth_service.change_own_password(account.id, PASSWORD, NEW_PASSWORD, NEW_PASSWORD)

    assert uow.users.get_by_id(account.id).password_hash == hashed(NEW_PASSWORD)
    assert uow.committed is True
    assert dto.id == account.id


def test_change_own_password_returns_a_fresh_session_and_drops_the_old_ones(auth_service, account):
    old = auth_service.authenticate("maria", PASSWORD).session_id

    fresh = auth_service.change_own_password(account.id, PASSWORD, NEW_PASSWORD, NEW_PASSWORD)

    assert fresh.session_id != old
    assert auth_service.load_session_user(old) is None
    assert auth_service.load_session_user(fresh.session_id) is not None


def test_change_own_password_warns_the_user_by_email(auth_service, emails, account):
    auth_service.change_own_password(account.id, PASSWORD, NEW_PASSWORD, NEW_PASSWORD)

    assert emails.last["to"] == "maria@example.com"
    assert "alterada" in emails.last["subject"].lower()
    assert NEW_PASSWORD not in emails.last["body"] and PASSWORD not in emails.last["body"]


def test_change_own_password_works_even_if_the_notification_cannot_be_sent(auth_service, uow, emails, account):
    emails.fail = True

    auth_service.change_own_password(account.id, PASSWORD, NEW_PASSWORD, NEW_PASSWORD)

    assert uow.users.get_by_id(account.id).password_hash == hashed(NEW_PASSWORD)


@pytest.mark.parametrize("current", ["errada-errada-1", "", None, PASSWORD + " ", PASSWORD.upper()])
def test_change_own_password_requires_the_current_password(auth_service, uow, emails, account, current):
    with pytest.raises(DomainValidationError, match="senha atual não confere") as exc:
        auth_service.change_own_password(account.id, current, NEW_PASSWORD, NEW_PASSWORD)

    assert exc.value.field == "current_password"
    assert uow.users.get_by_id(account.id).password_hash == account.password_hash
    assert emails.outbox == []
    assert uow.committed is False


@pytest.mark.parametrize("new, confirmation, message", [
    ("curta", "curta", "pelo menos 8 caracteres"),
    ("", "", "Senha é obrigatória"),
    (None, None, "Senha é obrigatória"),
    (NEW_PASSWORD, "outra-coisa-12345", "senhas informadas não conferem"),
    (NEW_PASSWORD, None, "senhas informadas não conferem"),
    (NEW_PASSWORD, NEW_PASSWORD + " ", "senhas informadas não conferem"),
    (PASSWORD, PASSWORD, "diferente da atual"),
])
def test_change_own_password_validates_the_new_password(auth_service, uow, account, new, confirmation, message):
    with pytest.raises(DomainValidationError, match=message):
        auth_service.change_own_password(account.id, PASSWORD, new, confirmation)

    assert uow.users.get_by_id(account.id).password_hash == account.password_hash
    assert uow.committed is False


@pytest.mark.parametrize("kind", ["missing", "deactivated", "pending"])
def test_change_own_password_of_an_account_that_cannot_log_in_is_not_found(auth_service, uow, kind):
    if kind == "missing":
        user_id = uuid.uuid4()
    elif kind == "deactivated":
        user_id = make_user(uow, active=False).id
    else:
        user_id = make_user(uow, activated=False).id

    with pytest.raises(EntityNotFoundError):
        auth_service.change_own_password(user_id, PASSWORD, NEW_PASSWORD, NEW_PASSWORD)


def test_change_own_password_keeps_the_account_activation_and_role(auth_service, uow, account):
    activated = account.activated_at
    auth_service.change_own_password(account.id, PASSWORD, NEW_PASSWORD, NEW_PASSWORD)

    stored = uow.users.get_by_id(account.id)
    assert (stored.activated_at, stored.role, stored.is_active) == (activated, Role.FAMILY_USER, True)


def test_the_old_password_stops_working_after_the_change(auth_service, account):
    auth_service.change_own_password(account.id, PASSWORD, NEW_PASSWORD, NEW_PASSWORD)

    with pytest.raises(AuthenticationFailedError):
        auth_service.authenticate("maria", PASSWORD)
    assert auth_service.authenticate("maria", NEW_PASSWORD)


def test_fake_hasher_sanity():
    assert FakePasswordHasher().verify("a", FakePasswordHasher().hash("a"))


def test_changing_the_password_revokes_a_recovery_link_sent_before(auth_service, credential_service, uow, emails, account):
    from fakes.identity_fakes import token_from_link

    credential_service.request_recovery("maria@example.com")
    token = token_from_link(emails.last["body"])
    credential_service.inspect_recovery(token)                       # o link vale agora

    auth_service.change_own_password(account.id, PASSWORD, NEW_PASSWORD, NEW_PASSWORD)

    with pytest.raises(AuthenticationFailedError):
        credential_service.inspect_recovery(token)
    with pytest.raises(AuthenticationFailedError):
        credential_service.complete_recovery(token, "outra-senha-qualquer-1", "outra-senha-qualquer-1")
    assert uow.invitations.get_active_for_user(account.id) is None
