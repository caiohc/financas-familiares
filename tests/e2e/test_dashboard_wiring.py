import re

import pytest
from sqlalchemy import create_engine

from app import create_app
from infrastructure.database.models import Base

@pytest.fixture
def client(tmp_path):
    """App real, fábricas de produção, sem doubles: só confirma o wiring do dashboard em app.py."""
    db_uri = f"sqlite:///{tmp_path / 'wiring_test.db'}"
    setup_engine = create_engine(db_uri)
    Base.metadata.create_all(setup_engine)
    setup_engine.dispose()
    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": db_uri, "SECRET_KEY": "x"}).test_client()

def test_dashboard_wiring_through_the_real_stack(client):
    client.post("/family/create", data={"name": "Família Wiring"})
    client.post("/user/create", data={
        "role": "SYSTEM_ADMIN", "name": "Caio", "username": "caio", "email": "caio@example.com",
        "temporary_password": "senha-temporaria", "temporary_password_confirmation": "senha-temporaria",
    })

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/family/list"' in html
    assert ">1<" in html
    user_row = re.search(r'<tr>(?:(?!</tr>).)*href="/user/list"(?:(?!</tr>).)*</tr>', html, re.S).group(0)
    assert "Usuários" in user_row and ">1<" in user_row
