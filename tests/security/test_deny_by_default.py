"""Negar por padrão: toda rota exige login, exceto as públicas declaradas. Uma rota nova sem proteção quebra aqui."""
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from werkzeug.routing import UUIDConverter

from interface.web.security import PUBLIC_ENDPOINTS

# As ÚNICAS rotas acessíveis sem login. Acrescentar uma é uma decisão de segurança: exige editar esta lista.
EXPECTED_PUBLIC = {
    "static",
    "auth.login", "auth.authenticate",
    "auth.activate", "auth.set_password",
    "auth.forgot_password", "auth.request_recovery",
    "auth.recover", "auth.reset_password",
}


def _sample_url(app, rule) -> str:
    values = {}
    for argument in rule.arguments:
        converter = rule._converters.get(argument)
        values[argument] = str(uuid.uuid4()) if isinstance(converter, UUIDConverter) else "x"
    return app.url_map.bind("localhost").build(rule.endpoint, values)


def _rules(app):
    return [r for r in app.url_map.iter_rules() if r.endpoint != "static"]


def test_the_public_endpoints_are_exactly_the_decided_ones():
    assert set(PUBLIC_ENDPOINTS) == EXPECTED_PUBLIC


def test_every_public_endpoint_really_exists(world):
    registered = {rule.endpoint for rule in world.app.url_map.iter_rules()}
    assert EXPECTED_PUBLIC <= registered


def test_every_non_public_route_redirects_an_anonymous_visitor_to_the_login(world):
    client = world.client()
    checked = 0

    for rule in _rules(world.app):
        if rule.endpoint in EXPECTED_PUBLIC:
            continue
        url = _sample_url(world.app, rule)
        for method in sorted(rule.methods & {"GET", "POST"}):
            response = client.open(url, method=method)
            assert response.status_code == 302, f"{method} {url} ({rule.endpoint}) está ABERTA: {response.status_code}"
            assert response.headers["Location"].startswith("/auth/login"), (method, url, response.headers["Location"])
            checked += 1

    assert checked > 40            # percorreu de verdade as rotas de todos os módulos


def test_a_protected_page_remembers_where_the_visitor_was_going(world):
    response = world.client().get("/member/list")

    assert response.status_code == 302
    location = urlparse(response.headers["Location"])
    assert location.path == "/auth/login" and parse_qs(location.query) == {"next": ["/member/list"]}


def test_no_data_page_leaks_content_to_an_anonymous_visitor(world):
    client = world.client()

    for url in ("/", "/family/list", "/member/list", "/cost-center/list", "/category/list", "/user/list"):
        response = client.get(url)
        assert response.status_code == 302 and b"<table" not in response.data, url


def test_every_route_of_every_blueprint_is_covered_by_the_walk(world):
    blueprints = {rule.endpoint.split(".")[0] for rule in _rules(world.app)}
    assert {"auth", "dashboard", "family", "family_cost_center", "member", "category", "user"} <= blueprints


def test_static_files_stay_public(world):
    assert world.client().get("/static/css/app.css").status_code == 200
    assert world.client().get("/static/js/password_toggle.js").status_code == 200


def test_an_unknown_url_is_a_404_not_a_redirect(world):
    assert world.client().get("/nao-existe").status_code in (302, 404)


@pytest.mark.parametrize("method", ["PUT", "DELETE", "PATCH"])
def test_unconventional_methods_never_reach_a_view(world, method):
    client = world.client()
    for url in ("/user/list", "/family/delete/" + str(uuid.uuid4()), "/auth/logout"):
        assert client.open(url, method=method).status_code in (302, 405)
