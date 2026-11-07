import re

import pytest
from sqlalchemy import create_engine

from app import create_app
from domain.identity.entities import Role
from infrastructure.database.models import Base
from infrastructure.security.password_hasher import WerkzeugPasswordHasher


@pytest.fixture
def app(tmp_path):
    """
    App real, fábricas de produção, sem doubles. Teste deliberadamente mínimo: só confirma que
    app.py conecta a fábrica e o blueprint de User. Regras de negócio ficam nos unitários e
    nos de integração do repositório.
    """
    db_uri = f"sqlite:///{tmp_path / 'wiring_test.db'}"
    setup_engine = create_engine(db_uri)
    Base.metadata.create_all(setup_engine)
    setup_engine.dispose()

    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": db_uri, "SECRET_KEY": "wiring-test-secret"})


@pytest.fixture
def client(app):
    return app.test_client()


def test_user_creation_rejects_a_mismatching_password_confirmation_through_the_real_stack(client):
    response = client.post("/user/create", data={
        "role": "SYSTEM_ADMIN", "name": "Caio", "username": "caio", "email": "caio@example.com",
        "temporary_password": "senha-temporaria", "temporary_password_confirmation": "senha-diferente",
    })

    assert response.status_code == 400
    assert "As senhas informadas não conferem." in response.get_data(as_text=True)
    assert "caio@example.com" not in client.get("/user/list").get_data(as_text=True)


def test_user_wiring_through_the_real_stack(app, client):
    family_page = client.post("/family/create", data={"name": "Família Wiring"}, follow_redirects=True)
    family_id = re.search(r"/family/edit/([0-9a-f-]{36})", family_page.get_data(as_text=True)).group(1)

    create_response = client.post("/user/create", data={
        "role": "FAMILY_ADMIN", "family_id": family_id, "name": "Maria Souza", "username": "maria",
        "email": "maria@example.com", "temporary_password": "senha-temporaria",
        "temporary_password_confirmation": "senha-temporaria",
    }, follow_redirects=True)
    assert create_response.status_code == 200
    assert "cadastrado com sucesso" in create_response.get_data(as_text=True)

    list_response = client.get("/user/list?sort=email&dir=desc&q=souza")
    assert list_response.status_code == 200
    html = list_response.get_data(as_text=True)
    assert "maria@example.com" in html
    assert "senha-temporaria" not in html

    with app.user_service_factory().uow as uow:
        user = uow.users.get_by_username("maria")
        assert (user.role, user.must_change_password) == (Role.FAMILY_ADMIN, True)
        assert WerkzeugPasswordHasher().verify("senha-temporaria", user.password_hash)
