import re

import pytest
from sqlalchemy import create_engine

from app import create_app
from infrastructure.database.models import Base

@pytest.fixture
def app(tmp_path):
    """
    App real, com a factory de produção (family_service_factory), sem nenhum
    double. Cobre wiring: rota -> serviço real -> SQLAlchemyUnitOfWork real ->
    banco real. Regras de negócio não são o alvo aqui (já cobertas nos
    unitários com fake); o alvo é só "as peças se encaixam?".
    """
    db_uri = f"sqlite:///{tmp_path / 'wiring_test.db'}"

    # init_db() não cria o schema de propósito (evolução do banco é manual,
    # via Alembic); aqui criamos direto pelos models, como no conftest de
    # integração dos repositórios.
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

def _extract_family_id(html: str) -> str:
    match = re.search(r"/family/edit/([0-9a-f-]{36})", html)
    assert match is not None, "esperava exatamente um link de edição na listagem"
    return match.group(1)

def test_family_full_lifecycle_through_the_real_stack(client):
    # Criar
    create_response = client.post(
        "/family/create", data={"name": "Família Wiring"}, follow_redirects=True
    )
    assert create_response.status_code == 200
    html = create_response.get_data(as_text=True)
    assert "Família Wiring" in html
    assert "criada com sucesso" in html

    family_id = _extract_family_id(html)

    # Editar (form pré-preenchido)
    edit_response = client.get(f"/family/edit/{family_id}")
    assert edit_response.status_code == 200
    assert 'value="Família Wiring"' in edit_response.get_data(as_text=True)

    # Atualizar
    update_response = client.post(
        f"/family/update/{family_id}",
        data={"name": "Família Wiring Renomeada"},
        follow_redirects=True,
    )
    assert update_response.status_code == 200
    updated_html = update_response.get_data(as_text=True)
    assert "Família Wiring Renomeada" in updated_html
    assert "atualizada com sucesso" in updated_html
    assert "Família Wiring</td>" not in updated_html

    # Excluir
    delete_response = client.post(f"/family/delete/{family_id}", follow_redirects=True)
    assert delete_response.status_code == 200
    deleted_html = delete_response.get_data(as_text=True)
    assert "excluída com sucesso" in deleted_html
    assert "Família Wiring Renomeada" not in deleted_html
    assert "Nenhuma família" in deleted_html
