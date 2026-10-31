import pytest
from unittest.mock import create_autospec

from app import create_app
from application.services.family_service import FamilyService
from application.services.family_cost_center_service import FamilyCostCenterService
from application.services.member_service import MemberService
from application.services.category_service import CategoryService
from application.services.dashboard_service import DashboardService

@pytest.fixture
def family_service():
    """Double do FamilyService: isola o controlador web da regra de negócio e da infra."""
    return create_autospec(FamilyService, instance=True)

@pytest.fixture
def family_cost_center_service():
    """Double do FamilyCostCenterService: isola o controlador web da regra de negócio e da infra."""
    return create_autospec(FamilyCostCenterService, instance=True)

@pytest.fixture
def member_service():
    """Double do MemberService: isola o controlador web da regra de negócio e da infra."""
    return create_autospec(MemberService, instance=True)

@pytest.fixture
def category_service():
    """Double do CategoryService: isola o controlador web da regra de negócio e da infra."""
    return create_autospec(CategoryService, instance=True)

@pytest.fixture
def dashboard_service():
    """Double do DashboardService: isola o controlador web da regra de negócio e da infra."""
    return create_autospec(DashboardService, instance=True)

@pytest.fixture
def app(family_service, family_cost_center_service, member_service, category_service, dashboard_service):
    """Cria o app Flask com config de teste e injeta os doubles dos serviços na factory."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key",
    })
    app.family_service_factory = lambda: family_service
    app.family_cost_center_service_factory = lambda: family_cost_center_service
    app.member_service_factory = lambda: member_service
    app.category_service_factory = lambda: category_service
    app.dashboard_service_factory = lambda: dashboard_service
    return app

@pytest.fixture
def client(app):
    """Cliente de testes do Flask: simula requisições HTTP sem subir servidor."""
    return app.test_client()
