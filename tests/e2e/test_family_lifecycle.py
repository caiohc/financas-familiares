import re

import pytest
from support import create_test_app

@pytest.fixture
def app(tmp_path):
    """
    App real, com a factory de produção (family_service_factory), sem nenhum
    double. Cobre wiring: rota -> serviço real -> SQLAlchemyUnitOfWork real ->
    banco real. Regras de negócio não são o alvo aqui (já cobertas nos
    unitários com fake); o alvo é só "as peças se encaixam?".
    """
    app = create_test_app(tmp_path)
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

def test_family_list_is_paginated_with_real_wiring(app):
    """Wiring da paginação: query string -> rota -> serviço real -> repositório SQL real."""
    client = app.test_client()
    for number in range(1, 13):
        client.post("/family/create", data={"name": f"Família {number:02d}"})

    client.get("/family/list")  # consome as mensagens flash das criações
    first = client.get("/family/list").get_data(as_text=True)
    second = client.get("/family/list?page=2").get_data(as_text=True)
    bigger = client.get("/family/list?per_page=25").get_data(as_text=True)

    assert "Página 1 de 2" in first and "Família 10" in first and "Família 11" not in first
    assert "Página 2 de 2" in second and "Família 11" in second and "Família 12" in second
    assert "Página 1 de 1" in bigger and "Família 12" in bigger

def test_family_list_sorting_with_real_wiring(app):
    """Wiring da ordenação: ?sort&dir -> rota -> serviço real -> repositório SQL real."""
    client = app.test_client()
    for name in ("Almeida", "Souza", "Costa"):
        client.post("/family/create", data={"name": name})
    client.get("/family/list")  # consome as mensagens flash das criações

    ascending = client.get("/family/list").get_data(as_text=True)
    descending = client.get("/family/list?sort=name&dir=desc").get_data(as_text=True)

    assert ascending.index("Almeida") < ascending.index("Costa") < ascending.index("Souza")
    assert descending.index("Souza") < descending.index("Costa") < descending.index("Almeida")
    assert 'aria-sort="descending"' in descending

def test_family_search_paginates_over_the_results_with_real_wiring(app):
    """Wiring da pesquisa: ?q -> rota -> serviço real -> repositório SQL real, com paginação sobre o resultado."""
    client = app.test_client()
    for number in range(1, 16):
        client.post("/family/create", data={"name": f"Silva {number:02d}"})
    for number in range(1, 21):
        client.post("/family/create", data={"name": f"Souza {number:02d}"})
    client.get("/family/list")  # consome as mensagens flash das criações

    first = client.get("/family/list?q=SILVA").get_data(as_text=True)
    second = client.get("/family/list?q=silva&page=2").get_data(as_text=True).replace("<mark>", "").replace("</mark>", "")
    accented = client.get("/family/list?q=sílva").get_data(as_text=True)
    none = client.get("/family/list?q=xyz").get_data(as_text=True)

    assert "Página 1 de 2" in first and "15 resultados" in first and "Souza" not in first
    assert "Silva 11" in second and "Silva 15" in second and "Souza" not in second
    assert "15 resultados" in accented
    assert "Nenhum resultado" in none
