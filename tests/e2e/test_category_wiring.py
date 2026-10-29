import json

import pytest
from sqlalchemy import create_engine

from app import create_app
from infrastructure.database.models import Base

def _app(tmp_path, **extra_config):
    db_uri = f"sqlite:///{tmp_path / 'wiring_test.db'}"
    setup_engine = create_engine(db_uri)
    Base.metadata.create_all(setup_engine)
    setup_engine.dispose()
    return create_app({
        "TESTING": True, "SQLALCHEMY_DATABASE_URI": db_uri, "SECRET_KEY": "wiring-test-secret", **extra_config,
    })

@pytest.fixture
def app(tmp_path):
    """App real, fábricas de produção, sem doubles: só confirma o wiring de Categoria em app.py."""
    return _app(tmp_path)

def test_category_wiring_through_the_real_stack(app):
    client = app.test_client()

    response = client.post("/category/create", data={"name": "Pets", "type": "EXPENSE"}, follow_redirects=True)
    assert response.status_code == 200
    assert "criada com sucesso" in response.get_data(as_text=True)

    assert "Pets" in client.get("/category/list").get_data(as_text=True)

def test_seed_categories_command_is_idempotent(tmp_path):
    defaults = tmp_path / "categories.json"
    defaults.write_text(
        json.dumps([{"name": "Alimentação", "type": "EXPENSE"}, {"name": "Salário", "type": "INCOME"}]),
        encoding="utf-8",
    )
    app = _app(tmp_path, CATEGORIES_PATH=str(defaults))
    runner = app.test_cli_runner()

    first = runner.invoke(args=["seed-categories"])
    second = runner.invoke(args=["seed-categories"])

    assert first.exit_code == 0, first.output
    assert "2 criada(s), 0 já existia(m)" in first.output
    assert "0 criada(s), 2 já existia(m)" in second.output
    listing = app.test_client().get("/category/list").get_data(as_text=True)
    assert "Alimentação" in listing and "Salário" in listing

def test_seed_categories_command_loads_the_project_default_file(tmp_path):
    # Sem CATEGORIES_PATH no test_config: usa o arquivo real do projeto. Uma entrada
    # inválida no JSON quebra este teste em vez de só aparecer ao rodar o comando.
    app = _app(tmp_path)

    result = app.test_cli_runner().invoke(args=["seed-categories"])

    assert result.exit_code == 0, result.output
    assert "16 criada(s), 0 já existia(m)" in result.output
