import re

import pytest
from sqlalchemy import create_engine

from app import create_app
from infrastructure.database.models import Base

@pytest.fixture
def app(tmp_path):
    """
    App real, com as factories de produção (family_service_factory e
    family_cost_center_service_factory), sem doubles. Ao contrário do teste
    de ciclo completo de Family, este é deliberadamente mínimo: seu único
    propósito é confirmar que app.py conecta a fábrica e o blueprint de
    FamilyCostCenter corretamente. Os testes de rota usam doubles injetados
    por fora, então não pegariam um erro de wiring em app.py (nome de
    atributo errado, blueprint não registrado). Regra de negócio já está
    coberta nos unitários/integração; não repetir aqui.
    """
    db_uri = f"sqlite:///{tmp_path / 'wiring_test.db'}"

    setup_engine = create_engine(db_uri)
    Base.metadata.create_all(setup_engine)
    setup_engine.dispose()

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": db_uri,
        "SECRET_KEY": "wiring-test-secret",
    })
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_family_cost_center_wiring_through_the_real_stack(client):
    create_family_response = client.post(
        "/family/create", data={"name": "Família Wiring"}, follow_redirects=True
    )
    family_id = re.search(r"/family/edit/([0-9a-f-]{36})", create_family_response.get_data(as_text=True)).group(1)

    create_response = client.post(
        f"/family/{family_id}/cost-center/create",
        data={"name": "Casa de Praia", "description": "Litoral"},
        follow_redirects=True,
    )
    assert create_response.status_code == 200
    html = create_response.get_data(as_text=True)
    assert "Casa de Praia" in html
    assert "criado com sucesso" in html

    list_response = client.get(f"/family/{family_id}/cost-center/list")
    assert list_response.status_code == 200
    assert "Casa de Praia" in list_response.get_data(as_text=True)
