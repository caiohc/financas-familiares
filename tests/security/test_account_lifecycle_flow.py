"""
Ciclo de vida das contas pelo HTTP, com a pilha real: do root ao usuário comum, convites, ativação, recuperação,
redefinição, desativação e tentativas de acesso cruzado entre famílias.
"""
import re
from datetime import datetime, timedelta
from html import unescape

import pytest
from sqlalchemy import text

from domain.identity.entities import Role
from domain.shared.clock import utcnow
from fakes.identity_fakes import token_from_link
from support import STRONG_PASSWORD

NEW_PASSWORD = "minha-nova-senha-segura-1"
INVALID_PAGE = "Link inválido, expirado ou já utilizado."


def _code_of(response) -> str:
    return re.search(r'id="invitation-code">([A-Z0-9-]+)<', response.get_data(as_text=True)).group(1)


def _create(world, client, role, username, family_id=None, name=None, email=None):
    email = email or f"{username}@example.com"
    data = {"role": role.value, "name": name or username.title(), "username": username, "email": email, "email_confirmation": email}
    if family_id:
        data["family_id"] = str(family_id)
    response = client.post("/user/create", data=data)
    assert response.status_code == 200, unescape(response.get_data(as_text=True))[:300]
    return _code_of(response), token_from_link(world.emails.last["body"])


def _activate(world, token, code, password=NEW_PASSWORD):
    return world.client().post(f"/auth/set-password/{token}", data={"code": code, "password": password, "password_confirmation": password})


def _flash_text(response) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", response.get_data(as_text=True)))


@pytest.fixture
def root_world(world):
    world.add_user("root", Role.ROOT)
    return world


@pytest.fixture
def family(world):
    return world.add_family("Família Silva")


# ---------------------------------------------------------------------------
# Root -> administrador do sistema -> administrador de família -> usuário
# ---------------------------------------------------------------------------

def test_the_whole_chain_from_root_to_a_family_user(root_world):
    world = root_world

    # 1. o root cadastra um administrador do sistema
    root = world.logged("root")
    code, token = _create(world, root, Role.SYSTEM_ADMIN, "caio", name="Caio Costa")
    assert world.login(world.client(), "caio", NEW_PASSWORD).status_code == 401         # ainda pendente
    assert _activate(world, token, code).status_code == 302
    sysadmin = world.logged("caio", NEW_PASSWORD)

    # 2. o administrador do sistema cria a família e o primeiro administrador dela
    family_id = world.add_family("Família Costa")
    code, token = _create(world, sysadmin, Role.FAMILY_ADMIN, "ana", family_id, "Ana Costa")
    assert _activate(world, token, code).status_code == 302
    family_admin = world.logged("ana", NEW_PASSWORD)

    # 3. o administrador da família cadastra um usuário da própria família
    code, token = _create(world, family_admin, Role.FAMILY_USER, "bia", family_id, "Bia Costa")
    assert _activate(world, token, code).status_code == 302
    family_user = world.logged("bia", NEW_PASSWORD)

    # 4. cada um enxerga o que o papel permite
    assert root.get("/user/list").status_code == 200
    assert sysadmin.get("/user/list").status_code == 200
    assert family_admin.get("/user/list").status_code == 200
    assert family_user.get("/user/list").status_code == 403
    assert family_user.get("/").status_code == 200


def test_the_created_account_starts_pending_with_no_password(root_world):
    root = root_world.logged("root")
    _create(root_world, root, Role.SYSTEM_ADMIN, "caio")

    row = root_world.user_row("caio")
    assert row.password_hash is None and row.activated_at is None


def test_the_code_page_shows_the_code_once_and_the_email_never_has_it(root_world):
    root = root_world.logged("root")
    code, _ = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")

    body = root_world.emails.last["body"]
    assert code not in body and code.replace("-", "") not in body
    assert "CÓDIGO" in body and "outro meio" in body
    assert code not in root.get("/user/list").get_data(as_text=True)


def test_nothing_is_stored_in_clear_text(root_world):
    root = root_world.logged("root")
    code, token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")

    with root_world._maker() as session:
        rows = session.execute(text("SELECT token_hash, code_hash FROM user_invitations")).fetchall()
    assert len(rows) == 1
    token_hash, code_hash = rows[0]
    assert token not in token_hash and code not in code_hash and code.replace("-", "") not in code_hash
    assert code_hash.startswith("$argon2id$") and len(token_hash) == 64


def test_the_activation_page_reveals_nothing_about_the_user(root_world):
    root = root_world.logged("root")
    _, token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio", name="Caio Costa", email="caio.secreto@example.com")

    html = root_world.client().get(f"/auth/activate/{token}").get_data(as_text=True)

    assert "Caio" not in html and "caio" not in html.lower().replace("código", "") and "secreto" not in html


# --- Ativação: link + código ---

def test_activation_with_the_wrong_code_fails_generically_and_the_account_stays_pending(root_world):
    root = root_world.logged("root")
    _, token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")

    response = _activate(root_world, token, "ZZZZ-ZZZZ")

    assert response.status_code == 400 and "Convite ou código inválido" in unescape(response.get_data(as_text=True))
    assert root_world.user_row("caio").password_hash is None


def test_after_five_wrong_codes_the_right_one_is_refused_too(root_world):
    root = root_world.logged("root")
    code, token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")

    for _ in range(5):
        assert _activate(root_world, token, "ZZZZ-ZZZZ").status_code == 400
    response = _activate(root_world, token, code)

    assert response.status_code == 400
    assert root_world.user_row("caio").password_hash is None
    assert root_world.client().get(f"/auth/activate/{token}").status_code == 400


def test_the_code_alone_or_the_link_alone_is_not_enough(root_world):
    root = root_world.logged("root")
    code, token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")

    assert _activate(root_world, token, "").status_code == 400
    assert _activate(root_world, "token-errado", code).status_code == 400
    assert root_world.user_row("caio").password_hash is None


def test_a_mismatching_password_keeps_the_invitation_usable(root_world):
    root = root_world.logged("root")
    code, token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")

    response = root_world.client().post(f"/auth/set-password/{token}", data={
        "code": code, "password": NEW_PASSWORD, "password_confirmation": "outra-coisa-12345",
    })

    assert response.status_code == 400 and "senhas informadas não conferem" in unescape(response.get_data(as_text=True))
    assert _activate(root_world, token, code).status_code == 302


@pytest.mark.parametrize("password", ["curta", "1234567", ""])
def test_a_weak_password_is_refused_with_the_policy_message(root_world, password):
    root = root_world.logged("root")
    code, token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")

    response = root_world.client().post(f"/auth/set-password/{token}", data={"code": code, "password": password, "password_confirmation": password})

    assert response.status_code == 400
    assert root_world.user_row("caio").password_hash is None


def test_the_code_may_be_typed_in_lowercase_without_the_hyphen(root_world):
    root = root_world.logged("root")
    code, token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")

    assert _activate(root_world, token, code.lower().replace("-", " ")).status_code == 302


def test_the_invitation_works_only_once(root_world):
    root = root_world.logged("root")
    code, token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")
    assert _activate(root_world, token, code).status_code == 302

    assert _activate(root_world, token, code, "outra-senha-forte-9").status_code == 400
    assert root_world.client().get(f"/auth/activate/{token}").status_code == 400
    assert root_world.login(root_world.client(), "caio", NEW_PASSWORD).status_code == 302


def test_an_expired_invitation_is_refused(root_world):
    root = root_world.logged("root")
    code, token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")
    with root_world._maker() as session:
        session.execute(text("UPDATE user_invitations SET expires_at = :past"), {"past": str(utcnow() - timedelta(minutes=1))})
        session.commit()

    assert root_world.client().get(f"/auth/activate/{token}").status_code == 400
    assert _activate(root_world, token, code).status_code == 400
    assert root_world.user_row("caio").password_hash is None


def test_every_kind_of_dead_link_shows_the_same_page(root_world):
    root = root_world.logged("root")
    code, token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")
    _activate(root_world, token, code)                                   # agora o link está usado
    _, expired = _create(root_world, root, Role.SYSTEM_ADMIN, "dora")
    with root_world._maker() as session:
        session.execute(text("UPDATE user_invitations SET expires_at = :past WHERE consumed_at IS NULL"), {"past": str(utcnow() - timedelta(hours=1))})
        session.commit()

    pages = {
        root_world.client().get(f"/auth/activate/{t}").get_data(as_text=True)
        for t in (token, expired, "nunca-existiu", "A" * 43)
    }

    assert len(pages) == 1 and INVALID_PAGE in unescape(pages.pop())


def test_a_recovery_link_is_not_an_activation_page(world, family):
    world.add_user("ana", Role.FAMILY_USER, family_id=family, email="ana@example.com")
    world.client().post("/auth/request-recovery", data={"email": "ana@example.com"})
    token = token_from_link(world.emails.last["body"])

    assert world.client().get(f"/auth/activate/{token}").status_code == 400
    assert world.client().get(f"/auth/recover/{token}").status_code == 200


# --- Reenviar o convite ---

def test_reissuing_kills_the_old_link_and_code(root_world):
    root = root_world.logged("root")
    old_code, old_token = _create(root_world, root, Role.SYSTEM_ADMIN, "caio")
    row = root_world.user_row("caio")

    response = root.post(f"/user/reissue-invitation/{row.id}")
    new_code = _code_of(response)
    new_token = token_from_link(root_world.emails.last["body"])

    assert new_code != old_code and new_token != old_token
    assert _activate(root_world, old_token, old_code).status_code == 400
    assert _activate(root_world, old_token, new_code).status_code == 400
    assert _activate(root_world, new_token, old_code).status_code == 400
    assert _activate(root_world, new_token, new_code).status_code == 302


def test_the_pending_email_may_be_corrected_by_the_administrator(root_world):
    root = root_world.logged("root")
    _create(root_world, root, Role.SYSTEM_ADMIN, "caio", email="errado@example.com")
    row = root_world.user_row("caio")

    response = root.post(f"/user/update/{row.id}", data={"name": "Caio", "username": "caio", "email": "certo@example.com"})

    assert response.status_code == 302 and root_world.user_row("caio").email == "certo@example.com"


# ---------------------------------------------------------------------------
# E-mail travado depois da ativação
# ---------------------------------------------------------------------------

def test_nobody_can_change_the_email_of_an_activated_account(world, family):
    world.add_user("admin", Role.SYSTEM_ADMIN)
    world.add_user("ana", Role.FAMILY_ADMIN, family_id=family, email="ana@example.com")
    ana_id = world.user_row("ana").id
    boss = world.logged("admin")

    response = boss.post(f"/user/update/{ana_id}", data={"name": "Ana", "username": "ana", "email": "invasor@example.com"})

    assert response.status_code == 400
    assert "depois que a conta foi ativada" in unescape(response.get_data(as_text=True))
    assert world.user_row("ana").email == "ana@example.com"


def test_the_edit_page_of_an_activated_account_has_no_editable_email(world, family):
    world.add_user("admin", Role.SYSTEM_ADMIN)
    world.add_user("ana", Role.FAMILY_USER, family_id=family, email="ana@example.com")

    html = world.logged("admin").get(f"/user/edit/{world.user_row('ana').id}").get_data(as_text=True)

    assert not re.search(r'<input[^>]*type="email"', html) and "ana@example.com" in html


# ---------------------------------------------------------------------------
# Redefinição de administrador do sistema (link + código)
# ---------------------------------------------------------------------------

def test_a_system_admin_resets_a_peers_password_with_link_and_code(world):
    world.add_user("caio", Role.SYSTEM_ADMIN)
    world.add_user("dora", Role.SYSTEM_ADMIN, email="dora@example.com")
    caio = world.logged("caio")
    dora_old_session = world.logged("dora")
    dora_id = world.user_row("dora").id

    response = caio.post(f"/user/reissue-invitation/{dora_id}")
    code = _code_of(response)
    token = token_from_link(world.emails.last["body"])

    assert world.login(world.client(), "dora").status_code == 401                 # a senha antiga já não entra
    assert dora_old_session.get("/").status_code == 302                           # nem a sessão aberta
    assert _activate(world, token, code).status_code == 302
    assert world.login(world.client(), "dora", NEW_PASSWORD).status_code == 302
    assert any("alterada" in m["subject"].lower() for m in world.emails.to("dora@example.com"))


def test_a_system_admin_cannot_reset_their_own_password_this_way(world):
    world.add_user("caio", Role.SYSTEM_ADMIN)
    caio = world.logged("caio")

    assert caio.post(f"/user/reissue-invitation/{world.user_row('caio').id}").status_code == 403
    assert world.login(world.client(), "caio").status_code == 302                 # a senha segue valendo


def test_a_family_admin_cannot_reset_a_system_admin(world, family):
    world.add_user("caio", Role.SYSTEM_ADMIN)
    world.add_user("ana", Role.FAMILY_ADMIN, family_id=family)
    ana = world.logged("ana")

    assert ana.post(f"/user/reissue-invitation/{world.user_row('caio').id}").status_code == 404
    assert world.login(world.client(), "caio").status_code == 302


def test_nobody_resets_the_root_through_the_application(world):
    world.add_user("root", Role.ROOT)
    world.add_user("caio", Role.SYSTEM_ADMIN)
    root_id = world.user_row("root").id

    assert world.logged("caio").post(f"/user/reissue-invitation/{root_id}").status_code == 403
    assert world.login(world.client(), "root").status_code == 302


def test_the_root_can_reset_a_system_admin(world):
    world.add_user("root", Role.ROOT)
    world.add_user("caio", Role.SYSTEM_ADMIN)

    response = world.logged("root").post(f"/user/reissue-invitation/{world.user_row('caio').id}")

    assert response.status_code == 200 and _code_of(response)


def test_active_family_users_are_told_to_use_forgot_password(world, family):
    world.add_user("admin", Role.SYSTEM_ADMIN)
    world.add_user("ana", Role.FAMILY_USER, family_id=family)
    world.add_user("bia", Role.FAMILY_ADMIN, family_id=family)
    boss = world.logged("admin")

    for username in ("ana", "bia"):
        response = boss.post(f"/user/reissue-invitation/{world.user_row(username).id}", follow_redirects=True)
        assert "redefinem a senha por conta própria" in _flash_text(response)
        assert world.login(world.client(), username).status_code == 302            # a senha continua a mesma


# ---------------------------------------------------------------------------
# Recuperação autônoma ("Esqueci minha senha")
# ---------------------------------------------------------------------------

def _forgot(world, email):
    return world.client().post("/auth/request-recovery", data={"email": email})


def test_recovery_flow_for_a_family_user(world, family):
    world.add_user("ana", Role.FAMILY_USER, family_id=family, email="ana@example.com")
    old_session = world.logged("ana")

    assert _forgot(world, "ana@example.com").status_code == 200
    token = token_from_link(world.emails.last["body"])
    assert world.client().get(f"/auth/recover/{token}").status_code == 200
    response = world.client().post(f"/auth/reset-password/{token}", data={"password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD})

    assert response.status_code == 302 and response.headers["Location"].endswith("/auth/login")
    assert world.login(world.client(), "ana", NEW_PASSWORD).status_code == 302
    assert world.login(world.client(), "ana", STRONG_PASSWORD).status_code == 401
    assert old_session.get("/").status_code == 302                                    # a sessão antiga caiu
    assert "alterada" in world.emails.last["subject"].lower()


def test_the_recovery_link_is_single_use_and_the_password_does_not_change_twice(world, family):
    world.add_user("ana", Role.FAMILY_USER, family_id=family, email="ana@example.com")
    _forgot(world, "ana@example.com")
    token = token_from_link(world.emails.last["body"])
    world.client().post(f"/auth/reset-password/{token}", data={"password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD})

    again = world.client().post(f"/auth/reset-password/{token}", data={"password": "outra-senha-forte-9", "password_confirmation": "outra-senha-forte-9"})

    assert again.status_code == 400
    assert world.login(world.client(), "ana", NEW_PASSWORD).status_code == 302


def test_the_recovery_link_lasts_fifteen_minutes(world, family):
    world.add_user("ana", Role.FAMILY_USER, family_id=family, email="ana@example.com")
    _forgot(world, "ana@example.com")
    token = token_from_link(world.emails.last["body"])
    with world._maker() as session:
        row = session.execute(text("SELECT created_at, expires_at FROM user_invitations")).one()
    created, expires = (datetime.fromisoformat(v) if isinstance(v, str) else v for v in row)
    assert expires - created == timedelta(minutes=15)

    with world._maker() as session:
        session.execute(text("UPDATE user_invitations SET expires_at = :past"), {"past": str(utcnow() - timedelta(seconds=1))})
        session.commit()
    assert world.client().get(f"/auth/recover/{token}").status_code == 400


def test_the_recovery_response_is_identical_for_every_kind_of_account(world, family):
    world.add_user("ativo", Role.FAMILY_USER, family_id=family, email="ativo@example.com")
    world.add_user("pendente", Role.FAMILY_USER, family_id=family, email="pendente@example.com", password=None, activated=False)
    world.add_user("desativado", Role.FAMILY_USER, family_id=family, email="desativado@example.com", is_active=False)
    world.add_user("sysadmin", Role.SYSTEM_ADMIN, email="sysadmin@example.com")
    world.add_user("root", Role.ROOT, email="root@example.com")

    bodies = {
        _forgot(world, email).get_data(as_text=True)
        for email in ("ativo@example.com", "pendente@example.com", "desativado@example.com", "sysadmin@example.com",
                      "root@example.com", "ninguem@example.com", "lixo", "")
    }
    # só o primeiro enviou algo: os demais pedidos "parecem" iguais mas não geram nenhuma mensagem
    assert len(bodies) == 1
    assert [m["to"] for m in world.emails.outbox] == ["ativo@example.com"]


def test_the_root_and_system_admins_cannot_recover_by_email(world):
    world.add_user("root", Role.ROOT, email="root@example.com")
    world.add_user("caio", Role.SYSTEM_ADMIN, email="caio@example.com")

    _forgot(world, "root@example.com")
    _forgot(world, "caio@example.com")

    assert world.emails.outbox == []


@pytest.mark.parametrize("password", ["curta", ""])
def test_recovery_with_a_weak_password_keeps_the_link_alive(world, family, password):
    world.add_user("ana", Role.FAMILY_USER, family_id=family, email="ana@example.com")
    _forgot(world, "ana@example.com")
    token = token_from_link(world.emails.last["body"])

    response = world.client().post(f"/auth/reset-password/{token}", data={"password": password, "password_confirmation": password})

    assert response.status_code == 400
    assert world.client().get(f"/auth/recover/{token}").status_code == 200


# ---------------------------------------------------------------------------
# Desativar e reativar
# ---------------------------------------------------------------------------

def test_deactivation_blocks_login_and_recovery_and_reactivation_restores_them(world, family):
    world.add_user("admin", Role.SYSTEM_ADMIN)
    world.add_user("ana", Role.FAMILY_USER, family_id=family, email="ana@example.com")
    ana_id = world.user_row("ana").id
    boss = world.logged("admin")

    boss.post(f"/user/deactivate/{ana_id}")
    assert world.login(world.client(), "ana").status_code == 401
    _forgot(world, "ana@example.com")
    assert world.emails.outbox == []

    boss.post(f"/user/reactivate/{ana_id}")
    assert world.login(world.client(), "ana").status_code == 302


def test_a_link_sent_before_the_deactivation_stops_working(world, family):
    world.add_user("admin", Role.SYSTEM_ADMIN)
    world.add_user("ana", Role.FAMILY_USER, family_id=family, email="ana@example.com")
    _forgot(world, "ana@example.com")
    token = token_from_link(world.emails.last["body"])

    world.logged("admin").post(f"/user/deactivate/{world.user_row('ana').id}")

    assert world.client().get(f"/auth/recover/{token}").status_code == 400


def test_nobody_deactivates_or_deletes_their_own_account(world):
    world.add_user("admin", Role.SYSTEM_ADMIN)
    admin = world.logged("admin")
    me = world.user_row("admin").id

    admin.post(f"/user/deactivate/{me}")
    admin.post(f"/user/delete/{me}")

    assert world.login(world.client(), "admin").status_code == 302


def test_the_root_cannot_be_deactivated_or_deleted(world):
    world.add_user("root", Role.ROOT)
    world.add_user("admin", Role.SYSTEM_ADMIN)
    root_id = world.user_row("root").id
    admin = world.logged("admin")

    assert admin.post(f"/user/deactivate/{root_id}").status_code == 403
    assert admin.post(f"/user/delete/{root_id}", follow_redirects=True).status_code == 200
    assert world.login(world.client(), "root").status_code == 302


# ---------------------------------------------------------------------------
# Um administrador de família não alcança outra família
# ---------------------------------------------------------------------------

@pytest.fixture
def two_families(world):
    fam_a, fam_b = world.add_family("Família A"), world.add_family("Família B")
    world.add_user("admin_a", Role.FAMILY_ADMIN, family_id=fam_a)
    world.add_user("user_a", Role.FAMILY_USER, family_id=fam_a)
    world.add_user("admin_b", Role.FAMILY_ADMIN, family_id=fam_b)
    world.add_user("user_b", Role.FAMILY_USER, family_id=fam_b)
    world.add_user("pend_b", Role.FAMILY_USER, family_id=fam_b, password=None, activated=False)
    return world, fam_a, fam_b


def test_the_family_admins_listing_shows_only_its_own_family(two_families):
    world, *_ = two_families

    html = world.logged("admin_a").get("/user/list").get_data(as_text=True)

    assert "user_a" in html and "admin_a" in html
    assert "user_b" not in html and "admin_b" not in html and "pend_b" not in html


def test_the_family_admins_search_cannot_reach_other_families(two_families):
    world, *_ = two_families

    html = world.logged("admin_a").get("/user/list?q=user_b").get_data(as_text=True)

    assert "<td>user_b</td>" not in html and "Nenhum resultado" in html          # o termo digitado reaparece, o usuário não


@pytest.mark.parametrize("username", ["user_b", "admin_b", "pend_b"])
def test_a_family_admin_gets_404_for_any_action_on_another_familys_user(two_families, username):
    world, *_ = two_families
    admin_a = world.logged("admin_a")
    target = world.user_row(username).id
    probes = [
        admin_a.get(f"/user/edit/{target}"), admin_a.get(f"/user/confirm-delete/{target}"),
        admin_a.post(f"/user/update/{target}", data={"name": "X", "username": username, "email": "x@example.com"}),
        admin_a.post(f"/user/deactivate/{target}"), admin_a.post(f"/user/reactivate/{target}"),
        admin_a.post(f"/user/delete/{target}"), admin_a.post(f"/user/reissue-invitation/{target}"),
    ]

    assert [p.status_code for p in probes] == [404] * 7
    assert world.user_row(username).is_active is True


def test_a_missing_user_and_another_familys_user_answer_the_same(two_families):
    import uuid

    world, *_ = two_families
    admin_a = world.logged("admin_a")

    other = admin_a.get(f"/user/edit/{world.user_row('user_b').id}")
    missing = admin_a.get(f"/user/edit/{uuid.uuid4()}")

    assert other.status_code == missing.status_code == 404
    assert other.get_data() == missing.get_data()


def test_a_family_admin_cannot_create_users_in_another_family(two_families):
    world, fam_a, fam_b = two_families
    admin_a = world.logged("admin_a")

    response = admin_a.post("/user/create", data={
        "role": "FAMILY_USER", "family_id": str(fam_b), "name": "Intruso", "username": "intruso",
        "email": "i@example.com", "email_confirmation": "i@example.com",
    })

    assert response.status_code == 403 and world.emails.outbox == []


@pytest.mark.parametrize("role", ["SYSTEM_ADMIN", "ROOT"])
def test_a_family_admin_cannot_escalate_privileges_by_creating_higher_roles(two_families, role):
    world, fam_a, _ = two_families
    admin_a = world.logged("admin_a")

    response = admin_a.post("/user/create", data={
        "role": role, "name": "Intruso", "username": "intruso", "email": "i@example.com", "email_confirmation": "i@example.com",
    })

    assert response.status_code in (400, 403) and world.emails.outbox == []


def test_a_family_admin_without_choosing_a_family_creates_in_its_own(two_families):
    world, fam_a, _ = two_families
    admin_a = world.logged("admin_a")

    response = admin_a.post("/user/create", data={
        "role": "FAMILY_USER", "name": "Nova", "username": "nova", "email": "nova@example.com", "email_confirmation": "nova@example.com",
    })

    assert response.status_code == 200
    assert str(world.user_row("nova").family_id) == str(fam_a)


def test_the_family_admins_form_offers_only_its_own_family(two_families):
    world, fam_a, fam_b = two_families

    html = world.logged("admin_a").get("/user/new").get_data(as_text=True)

    assert f'value="{fam_a}"' in html and f'value="{fam_b}"' not in html
    assert 'value="SYSTEM_ADMIN"' not in html


def test_a_family_user_cannot_use_the_user_area_at_all(two_families):
    world, *_ = two_families
    user_a = world.logged("user_a")
    target = world.user_row("admin_a").id

    codes = [user_a.get("/user/list").status_code, user_a.get("/user/new").status_code,
             user_a.post("/user/create", data={}).status_code, user_a.post(f"/user/deactivate/{target}").status_code,
             user_a.post(f"/user/delete/{target}").status_code, user_a.post(f"/user/reissue-invitation/{target}").status_code]

    assert codes == [403] * 6
    assert world.user_row("admin_a").is_active is True


def test_every_forbidden_page_uses_the_generic_message(two_families):
    world, *_ = two_families
    html = world.logged("user_a").get("/user/list").get_data(as_text=True)

    assert "Acesso negado" in html and "user_b" not in html
