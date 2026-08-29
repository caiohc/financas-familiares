import pytest
import uuid
from flask.testing import FlaskClient

from app import create_app
from application.services.family_service import FamilyService
from fakes.family_fakes import FakeUnitOfWork
from domain.family.entities import Family

@pytest.fixture
def uow():
    """Fornece a Unidade de Trabalho fake para os testes E2E/Web."""
    return FakeUnitOfWork()

@pytest.fixture
def family_service(uow):
    """Retorna a instância do serviço com o Fake UoW injetado."""
    return FamilyService(uow)

@pytest.fixture
def app(family_service):
    """Cria o aplicativo Flask e injeta o Serviço Fake por fora (Monkey Patching)."""
    app = create_app()
    # Substituímos a fábrica real (SQL) por uma que retorna o nosso Serviço Fake
    app.family_service_factory = lambda: family_service
    yield app

@pytest.fixture
def client(app):
    """O Cliente de Testes do Flask. Finge ser um navegador de forma super veloz."""
    return app.test_client()
