import re

import pytest
from support import create_test_app

@pytest.fixture
def app(tmp_path):
    """
    App real, fábricas de produção, sem doubles. Teste deliberadamente mínimo:
    só confirma que app.py conecta a fábrica e o blueprint de Member. Regras de
    negócio ficam nos unitários e nos de integração do repositório.
    """
    return create_test_app(tmp_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_member_wiring_through_the_real_stack(client):
    create_family_response = client.post("/family/create", data={"name": "Família Wiring"}, follow_redirects=True)
    family_id = re.search(r"/family/edit/([0-9a-f-]{36})", create_family_response.get_data(as_text=True)).group(1)

    create_response = client.post(
        "/member/create", data={"family_id": family_id, "name": "João"}, follow_redirects=True
    )
    assert create_response.status_code == 200
    assert "cadastrado com sucesso" in create_response.get_data(as_text=True)

    list_response = client.get("/member/list")
    assert list_response.status_code == 200
    assert "João" in list_response.get_data(as_text=True)
