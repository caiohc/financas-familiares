import re

import pytest

from domain.identity.entities import Role
from support import create_test_app


@pytest.fixture
def app(tmp_path):
    """
    App real, fábricas de produção, sem doubles. Teste deliberadamente mínimo: só confirma que app.py conecta as
    fábricas e o blueprint de User. Regras de negócio ficam nos unitários; os fluxos de segurança, em tests/security.
    """
    return create_test_app(tmp_path)


@pytest.fixture
def client(app):
    return app.test_client()


def test_user_wiring_through_the_real_stack(app, client):
    family_page = client.post("/family/create", data={"name": "Família Wiring"}, follow_redirects=True)
    family_id = re.search(r"/family/edit/([0-9a-f-]{36})", family_page.get_data(as_text=True)).group(1)

    create_response = client.post("/user/create", data={
        "role": "FAMILY_ADMIN", "family_id": family_id, "name": "Maria Souza", "username": "maria",
        "email": "maria@example.com", "email_confirmation": "maria@example.com",
    })
    assert create_response.status_code == 200
    assert "Código de ativação" in create_response.get_data(as_text=True)

    html = client.get("/user/list?sort=email&dir=desc&q=souza").get_data(as_text=True)
    assert "maria@example.com" in html and "Pendente de ativação" in html


def test_the_new_account_is_pending_without_a_password(app, client):
    family_page = client.post("/family/create", data={"name": "Família Wiring"}, follow_redirects=True)
    family_id = re.search(r"/family/edit/([0-9a-f-]{36})", family_page.get_data(as_text=True)).group(1)

    client.post("/user/create", data={
        "role": "FAMILY_USER", "family_id": family_id, "name": "João", "username": "joao",
        "email": "joao@example.com", "email_confirmation": "joao@example.com",
    })

    with app.app_context(), app.user_service_factory().uow as uow:
        user = uow.users.get_by_username("joao")
        assert user.role is Role.FAMILY_USER and user.password_hash is None and user.is_pending
        assert uow.invitations.get_active_for_user(user.id) is not None


def test_user_creation_rejects_mismatching_emails_through_the_real_stack(client):
    response = client.post("/user/create", data={
        "role": "SYSTEM_ADMIN", "name": "Caio", "username": "caio", "email": "caio@example.com",
        "email_confirmation": "outro@example.com",
    })

    assert response.status_code == 400
    assert "e-mails informados não conferem" in response.get_data(as_text=True)
    assert "caio@example.com" not in client.get("/user/list").get_data(as_text=True)
