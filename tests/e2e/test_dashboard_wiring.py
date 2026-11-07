import re

import pytest
from support import create_test_app

@pytest.fixture
def client(tmp_path):
    """App real, fábricas de produção, sem doubles: só confirma o wiring do dashboard em app.py."""
    return create_test_app(tmp_path).test_client()

def test_dashboard_wiring_through_the_real_stack(client):
    client.post("/family/create", data={"name": "Família Wiring"})
    client.post("/user/create", data={
        "role": "SYSTEM_ADMIN", "name": "Caio", "username": "caio", "email": "caio@example.com",
        "email_confirmation": "caio@example.com",
    })

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/family/list"' in html
    assert ">1<" in html
    user_row = re.search(r'<tr>(?:(?!</tr>).)*href="/user/list"(?:(?!</tr>).)*</tr>', html, re.S).group(0)
    # o usuário de desenvolvimento (criado pelo auxiliar de teste) e o "caio" cadastrado acima
    assert "Usuários" in user_row and ">2<" in user_row
