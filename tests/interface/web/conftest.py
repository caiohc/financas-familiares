import uuid

import pytest
from unittest.mock import create_autospec

from app import create_app
from application.dtos.identity_dtos import SessionUserDTO
from application.services.auth_service import AuthService
from application.services.credential_service import CredentialService
from application.services.family_service import FamilyService
from application.services.family_cost_center_service import FamilyCostCenterService
from application.services.member_service import MemberService
from application.services.category_service import CategoryService
from application.services.dashboard_service import DashboardService
from application.services.user_service import UserService
from domain.identity.entities import Role
from support import BASE_APP_CONFIG, DEV_USER

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
def user_service():
    """Double do UserService: isola o controlador web da regra de negócio e da infra."""
    return create_autospec(UserService, instance=True)

@pytest.fixture
def category_service():
    """Double do CategoryService: isola o controlador web da regra de negócio e da infra."""
    return create_autospec(CategoryService, instance=True)

@pytest.fixture
def dashboard_service():
    """Double do DashboardService: isola o controlador web da regra de negócio e da infra."""
    return create_autospec(DashboardService, instance=True)

@pytest.fixture
def dev_user():
    """O usuário como o qual a aplicação autentica sozinha nos testes de rota (administrador do sistema)."""
    return SessionUserDTO(
        id=uuid.uuid4(), role=Role.SYSTEM_ADMIN, family_id=None, name="Administrador de Teste",
        username=DEV_USER, email="dev@example.com", session_id="dev-session",
    )

@pytest.fixture
def auth_service(dev_user):
    """Double do AuthService: entrega o usuário de desenvolvimento ao carregador de sessão."""
    service = create_autospec(AuthService, instance=True)
    service.find_session_user_by_username.return_value = dev_user
    return service

@pytest.fixture
def credential_service():
    return create_autospec(CredentialService, instance=True)

@pytest.fixture
def app(family_service, family_cost_center_service, member_service, user_service, category_service,
        dashboard_service, auth_service, credential_service):
    """Cria o app Flask com config de teste e injeta os doubles dos serviços na factory."""
    app = create_app({
        **BASE_APP_CONFIG,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    app.family_service_factory = lambda: family_service
    app.family_cost_center_service_factory = lambda: family_cost_center_service
    app.member_service_factory = lambda: member_service
    app.user_service_factory = lambda: user_service
    app.category_service_factory = lambda: category_service
    app.dashboard_service_factory = lambda: dashboard_service
    app.auth_service_factory = lambda: auth_service
    app.credential_service_factory = lambda: credential_service
    return app

@pytest.fixture
def client(app):
    """Cliente de testes do Flask: simula requisições HTTP sem subir servidor."""
    return app.test_client()
