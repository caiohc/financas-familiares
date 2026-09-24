import pytest
from unittest.mock import create_autospec

from app import create_app
from application.services.family_service import FamilyService

@pytest.fixture
def family_service():
    """Double do FamilyService: isola o controlador web da regra de negócio e da infra."""
    return create_autospec(FamilyService, instance=True)

@pytest.fixture
def app(family_service):
    """Cria o app Flask com config de teste e injeta o double do serviço na factory."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key",
    })
    app.family_service_factory = lambda: family_service
    yield app

@pytest.fixture
def client(app):
    """Cliente de testes do Flask: simula requisições HTTP sem subir servidor."""
    return app.test_client()
