import pytest

from application.security_settings import SecuritySettings
from application.services.access_manager import AccessManager
from application.services.auth_service import AuthService
from application.services.credential_service import CredentialService
from application.services.user_service import UserService
from fakes.family_fakes import FakeUnitOfWork
from fakes.identity_fakes import FakeClock, FakeEmailSender, FakeLinkBuilder, FakePasswordHasher

SECRET_KEY = "chave-secreta-de-teste"


@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def hasher():
    return FakePasswordHasher()


@pytest.fixture
def emails():
    return FakeEmailSender()


@pytest.fixture
def settings():
    return SecuritySettings()


@pytest.fixture
def access_manager(hasher, emails, settings, clock):
    return AccessManager(hasher, emails, FakeLinkBuilder(), settings, clock)


@pytest.fixture
def user_service(uow, hasher, access_manager, clock):
    return UserService(uow, hasher, access_manager, clock)


@pytest.fixture
def auth_service(uow, hasher, access_manager, clock):
    return AuthService(uow, hasher, access_manager, SECRET_KEY, clock)


@pytest.fixture
def credential_service(uow, hasher, access_manager, settings, clock):
    return CredentialService(uow, hasher, access_manager, settings, clock)
