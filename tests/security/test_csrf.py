"""CSRF: nenhum POST altera estado sem o token da sessão. Um site de terceiros não consegue forjar a requisição."""
import re
import uuid

import pytest
from werkzeug.routing import UUIDConverter

from domain.identity.entities import Role
from infrastructure.database.models import UserModel
from support import STRONG_PASSWORD
from conftest import csrf_token_from


@pytest.fixture
def csrf_world(make_world):
    world = make_world(WTF_CSRF_ENABLED=True)
    world.add_user("admin", Role.SYSTEM_ADMIN)
    return world


def _post_rules(app):
    return [r for r in app.url_map.iter_rules() if r.endpoint != "static" and "POST" in r.methods]


def _url(app, rule) -> str:
    values = {a: (str(uuid.uuid4()) if isinstance(rule._converters.get(a), UUIDConverter) else "x") for a in rule.arguments}
    return app.url_map.bind("localhost").build(rule.endpoint, values)


def _logged_with_token(world):
    """Entra de verdade (com o token da página de login) e devolve o cliente e um token válido da sessão nova."""
    client = world.client()
    token = csrf_token_from(client.get("/auth/login").get_data(as_text=True))
    assert client.post("/auth/authenticate", data={"identifier": "admin", "password": STRONG_PASSWORD, "csrf_token": token}).status_code == 302
    return client, csrf_token_from(client.get("/user/new").get_data(as_text=True))


def test_every_post_endpoint_is_protected_for_an_anonymous_visitor(csrf_world):
    client = csrf_world.client()
    rules = _post_rules(csrf_world.app)

    for rule in rules:
        response = client.post(_url(csrf_world.app, rule), data={})
        assert response.status_code == 400, f"POST {rule.rule} aceitou uma requisição sem token: {response.status_code}"

    assert len(rules) >= 20


def test_every_post_endpoint_is_protected_for_a_logged_in_user_too(csrf_world):
    client, _ = _logged_with_token(csrf_world)

    for rule in _post_rules(csrf_world.app):
        response = client.post(_url(csrf_world.app, rule), data={})
        assert response.status_code == 400, f"POST {rule.rule} (logado) aceitou uma requisição sem token"


def test_the_rejection_page_is_generic(csrf_world):
    html = csrf_world.client().post("/auth/authenticate", data={"identifier": "admin", "password": STRONG_PASSWORD}).get_data(as_text=True)

    assert "Requisição inválida" in html and "admin" not in html


@pytest.mark.parametrize("token", ["", " ", "token-qualquer", "a" * 200, "ImZvbyI.aaaaaa.bbbbbbbbbbbbbbbbbbbbbbbb", "None"])
def test_garbage_tokens_are_rejected(csrf_world, token):
    client = csrf_world.client()
    client.get("/auth/login")            # abre a sessão

    response = client.post("/auth/authenticate", data={"identifier": "admin", "password": STRONG_PASSWORD, "csrf_token": token})

    assert response.status_code == 400


def test_a_token_from_another_session_is_rejected(csrf_world):
    mine, other = csrf_world.client(), csrf_world.client()
    token_of_other = csrf_token_from(other.get("/auth/login").get_data(as_text=True))
    mine.get("/auth/login")

    response = mine.post("/auth/authenticate", data={"identifier": "admin", "password": STRONG_PASSWORD, "csrf_token": token_of_other})

    assert response.status_code == 400


def test_a_valid_token_lets_the_request_through(csrf_world):
    client = csrf_world.client()
    token = csrf_token_from(client.get("/auth/login").get_data(as_text=True))

    response = client.post("/auth/authenticate", data={"identifier": "admin", "password": STRONG_PASSWORD, "csrf_token": token})

    assert response.status_code == 302 and response.headers["Location"] == "/"


def test_the_token_also_works_in_the_header_for_scripted_clients(csrf_world):
    client, token = _logged_with_token(csrf_world)

    response = client.post("/auth/logout", headers={"X-CSRFToken": token})

    assert response.status_code == 302


def test_a_forged_cross_site_request_has_no_effect(csrf_world):
    """Um site de terceiros faz o navegador da vítima (logada) enviar o POST, mas não consegue o token."""
    csrf_world.add_user("alvo", Role.FAMILY_USER)
    victim, _ = _logged_with_token(csrf_world)
    target_id = csrf_world.user_row("alvo").id

    forged = victim.post(f"/user/deactivate/{target_id}")
    forged_delete = victim.post(f"/user/delete/{target_id}")
    forged_create = victim.post("/user/create", data={"role": "SYSTEM_ADMIN", "name": "Invasor", "username": "invasor", "email": "i@example.com", "email_confirmation": "i@example.com"})

    assert (forged.status_code, forged_delete.status_code, forged_create.status_code) == (400, 400, 400)
    assert csrf_world.user_row("alvo").is_active is True
    with csrf_world._maker() as session:
        assert session.query(UserModel).filter(UserModel.username == "invasor").count() == 0


def test_the_logout_cannot_be_forced_from_another_site(csrf_world):
    client, _ = _logged_with_token(csrf_world)

    assert client.post("/auth/logout").status_code == 400
    assert client.get("/").status_code == 200           # continua logado


def test_the_password_change_cannot_be_forged(csrf_world):
    client, _ = _logged_with_token(csrf_world)

    response = client.post("/auth/update-password", data={
        "current_password": STRONG_PASSWORD, "password": "senha-do-invasor-1", "password_confirmation": "senha-do-invasor-1",
    })

    assert response.status_code == 400
    # a senha NÃO mudou: a antiga continua entrando, e a do invasor não
    fresh = csrf_world.client()
    token = csrf_token_from(fresh.get("/auth/login").get_data(as_text=True))
    assert fresh.post("/auth/authenticate", data={"identifier": "admin", "password": "senha-do-invasor-1", "csrf_token": token}).status_code == 401
    assert fresh.post("/auth/authenticate", data={"identifier": "admin", "password": STRONG_PASSWORD, "csrf_token": token}).status_code == 302


# --- Todo formulário POST renderizado carrega o token ---

def _forms(html: str):
    return re.findall(r"<form[^>]*>.*?</form>", html, re.S)


def test_every_rendered_post_form_carries_the_token(csrf_world):
    client, token = _logged_with_token(csrf_world)
    family = csrf_world.add_family("Silva")
    csrf_world.add_user("alvo", Role.FAMILY_USER, family_id=family)
    csrf_world.add_user("pendente", Role.FAMILY_USER, family_id=family, password=None, activated=False)
    target_id = csrf_world.user_row("alvo").id
    # uma família, um membro, um centro de custo e uma categoria reais, para as telas de edição e exclusão
    client.post("/member/create", data={"family_id": str(family), "name": "Membro", "csrf_token": token})
    client.post("/cost-center/create", data={"family_id": str(family), "name": "Centro", "csrf_token": token})
    client.post("/category/create", data={"name": "Categoria", "type": "EXPENSE", "csrf_token": token})

    pages = [
        "/user/new", "/user/list", f"/user/edit/{target_id}", f"/user/confirm-delete/{target_id}",
        "/family/new", "/family/list", "/member/new", "/member/list", "/cost-center/new", "/cost-center/list",
        "/category/new", "/category/list", "/auth/change-password",
    ]
    inspected = 0
    for page in pages:
        response = client.get(page)
        assert response.status_code == 200, page
        for form in _forms(response.get_data(as_text=True)):
            if re.search(r'method="post"', form, re.I):
                assert 'name="csrf_token"' in form, f"formulário POST sem token em {page}: {form[:120]}"
                inspected += 1

    assert inspected >= 12


def test_the_public_forms_carry_the_token_too(csrf_world):
    client = csrf_world.client()
    for page in ("/auth/login", "/auth/forgot-password"):
        forms = [f for f in _forms(client.get(page).get_data(as_text=True)) if re.search(r'method="post"', f, re.I)]
        assert forms and all('name="csrf_token"' in f for f in forms), page
