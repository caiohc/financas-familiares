"""Limite de tentativas, cabeçalhos de segurança e os links enviados por e-mail (envenenamento do cabeçalho Host)."""
import re

import pytest

from domain.identity.entities import Role
from fakes.identity_fakes import token_from_link
from support import STRONG_PASSWORD


# ---------------------------------------------------------------------------
# Limite de tentativas (Flask-Limiter)
# ---------------------------------------------------------------------------

@pytest.fixture
def limited(make_world):
    world = make_world(RATELIMIT_ENABLED=True)
    world.add_user("admin", Role.SYSTEM_ADMIN)
    world.add_user("outra", Role.SYSTEM_ADMIN)
    return world


def test_login_is_limited_to_five_attempts_per_minute_per_account(limited):
    client = limited.client()
    statuses = [limited.login(client, "admin", "errada-errada-1").status_code for _ in range(6)]

    assert statuses == [401, 401, 401, 401, 401, 429]


def test_after_the_limit_even_the_right_password_is_refused(limited):
    client = limited.client()
    for _ in range(5):
        limited.login(client, "admin", "errada-errada-1")

    response = limited.login(client, "admin", STRONG_PASSWORD)

    assert response.status_code == 429          # a força bruta não "acerta" na tentativa seguinte
    assert client.get("/").status_code == 302


def test_the_limit_page_is_generic_and_says_to_wait(limited):
    client = limited.client()
    for _ in range(5):
        limited.login(client, "admin", "errada-errada-1")

    html = limited.login(client, "admin", "errada-errada-1").get_data(as_text=True)

    assert "Muitas tentativas" in html and "Aguarde" in html


def test_locking_one_account_does_not_lock_the_others(limited):
    client = limited.client()
    for _ in range(6):
        limited.login(client, "admin", "errada-errada-1")

    assert limited.login(client, "outra", STRONG_PASSWORD).status_code == 302


def test_the_account_limit_ignores_case_and_spaces_so_it_cannot_be_dodged(limited):
    client = limited.client()
    variants = ["admin", "ADMIN", " admin ", "Admin", "aDmIn", "admin"]
    statuses = [limited.login(client, name, "errada-errada-1").status_code for name in variants]

    assert statuses[-1] == 429


def test_the_limit_for_nonexistent_accounts_is_the_same_so_it_reveals_nothing(limited):
    client = limited.client()
    statuses = [limited.login(client, "fantasma", "errada-errada-1").status_code for _ in range(6)]

    assert statuses == [401, 401, 401, 401, 401, 429]


def test_a_single_address_is_limited_across_many_accounts(limited):
    client = limited.client()
    statuses = [limited.login(client, f"conta{n}", "errada-errada-1").status_code for n in range(35)]

    assert statuses[:30] == [401] * 30 and set(statuses[30:]) == {429}


def test_password_recovery_requests_are_limited_per_email(limited):
    limited.add_user("ana", Role.FAMILY_USER, email="ana@example.com")
    client = limited.client()

    statuses = [client.post("/auth/request-recovery", data={"email": "ana@example.com"}).status_code for _ in range(4)]

    assert statuses == [200, 200, 200, 429]
    assert len(limited.emails.outbox) == 3         # e-mail bombing: no máximo três mensagens por hora


def test_the_recovery_limit_applies_to_unknown_emails_too(limited):
    client = limited.client()

    statuses = [client.post("/auth/request-recovery", data={"email": "ninguem@example.com"}).status_code for _ in range(4)]

    assert statuses == [200, 200, 200, 429]


def test_setting_a_password_with_a_code_is_limited(limited):
    client = limited.client()
    statuses = [client.post("/auth/set-password/token-qualquer", data={"code": "AAAA-AAAA", "password": "x", "password_confirmation": "x"}).status_code for _ in range(12)]

    assert statuses.count(429) >= 2 and statuses[0] == 400


def test_the_password_change_is_limited_per_user(limited):
    client = limited.logged("admin")
    data = {"current_password": "errada-errada-1", "password": "nova-senha-forte-1", "password_confirmation": "nova-senha-forte-1"}

    statuses = [client.post("/auth/update-password", data=data).status_code for _ in range(6)]

    assert statuses == [400, 400, 400, 400, 400, 429]


# ---------------------------------------------------------------------------
# Cabeçalhos de segurança
# ---------------------------------------------------------------------------

@pytest.fixture
def admin(world):
    world.add_user("admin", Role.SYSTEM_ADMIN)
    return world


@pytest.mark.parametrize("path", ["/auth/login", "/auth/forgot-password", "/auth/activate/x", "/auth/recover/x"])
def test_public_pages_carry_the_security_headers(admin, path):
    headers = admin.client().get(path).headers

    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("path", ["/", "/user/list", "/family/list", "/member/list", "/category/list"])
def test_authenticated_pages_carry_the_security_headers_and_are_not_cacheable(admin, path):
    headers = admin.logged("admin").get(path).headers

    assert headers["X-Frame-Options"] == "DENY" and headers["Referrer-Policy"] == "no-referrer"
    assert headers["Cache-Control"] == "no-store"          # a página de um usuário não fica no cache do navegador


def test_redirects_carry_the_headers_too(admin):
    headers = admin.client().get("/").headers
    assert headers["X-Frame-Options"] == "DENY"


def test_static_files_are_cacheable_but_still_not_sniffed(admin):
    headers = admin.client().get("/static/css/app.css").headers

    assert "no-store" not in headers.get("Cache-Control", "")
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_the_token_pages_never_leak_the_url_through_the_referer(admin):
    """O link de convite/recuperação traz o token na URL: o navegador não pode repassá-lo a nenhum site."""
    response = admin.client().get("/auth/recover/" + "t" * 43)

    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "http" not in re.sub(r'(href|action|src)="/[^"]*"', "", response.get_data(as_text=True)).split("<main")[1]


# ---------------------------------------------------------------------------
# Links de e-mail e o cabeçalho Host
# ---------------------------------------------------------------------------

def _request_recovery(world, host: str):
    world.add_user("ana", Role.FAMILY_USER, email="ana@example.com")
    client = world.client()
    client.post("/auth/request-recovery", data={"email": "ana@example.com"}, base_url=f"http://{host}")
    return world.emails.last["body"]


def test_with_a_configured_base_url_a_forged_host_header_cannot_poison_the_link(make_world):
    """Um atacante pede a recuperação da senha de uma vítima com 'Host: evil': o e-mail legítimo apontaria para ele."""
    world = make_world(APP_BASE_URL="https://financas.example.org")

    body = _request_recovery(world, "evil.example")

    assert "https://financas.example.org/auth/recover/" in body
    assert "evil.example" not in body


def test_the_configured_base_url_is_used_for_the_invitation_link_too(make_world):
    world = make_world(APP_BASE_URL="https://financas.example.org/")
    world.add_user("admin", Role.SYSTEM_ADMIN)
    client = world.client()
    evil = "http://evil.example"          # o cookie é por domínio: entra e age pelo mesmo Host forjado
    assert client.post("/auth/authenticate", data={"identifier": "admin", "password": STRONG_PASSWORD}, base_url=evil).status_code == 302

    client.post("/user/create", data={
        "role": "SYSTEM_ADMIN", "name": "Novo", "username": "novo", "email": "novo@example.com",
        "email_confirmation": "novo@example.com",
    }, base_url="http://evil.example")

    body = world.emails.last["body"]
    assert "https://financas.example.org/auth/activate/" in body and "evil.example" not in body
    assert "org//auth" not in body                      # a barra final da configuração não duplica


def test_without_a_base_url_development_falls_back_to_the_request_host(world):
    body = _request_recovery(world, "localhost:5000")
    assert "http://localhost:5000/auth/recover/" in body


def test_the_emailed_link_works_on_the_real_page(make_world):
    world = make_world(APP_BASE_URL="https://financas.example.org")
    body = _request_recovery(world, "localhost")
    token = token_from_link(body)

    assert world.client().get(f"/auth/recover/{token}").status_code == 200
