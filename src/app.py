from datetime import timedelta

from flask import Flask, current_app
from config import Config
from infrastructure.database.database import init_db
from security_config import validate_security_config

def family_service_factory():
    """Fábrica padrão para uso em produção (com SQLAlchemy real)."""
    from infrastructure.database.database import SessionLocal
    from infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
    from application.services.family_service import FamilyService

    # Injeta a fábrica de sessões (SessionLocal) no UoW.
    uow = SQLAlchemyUnitOfWork(SessionLocal)
    return FamilyService(uow=uow)

def family_cost_center_service_factory():
    """Fábrica padrão para uso em produção (com SQLAlchemy real)."""
    from infrastructure.database.database import SessionLocal
    from infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
    from application.services.family_cost_center_service import FamilyCostCenterService

    uow = SQLAlchemyUnitOfWork(SessionLocal)
    return FamilyCostCenterService(uow=uow)

def member_service_factory():
    """Fábrica padrão para uso em produção (com SQLAlchemy real)."""
    from infrastructure.database.database import SessionLocal
    from infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
    from application.services.member_service import MemberService

    uow = SQLAlchemyUnitOfWork(SessionLocal)
    return MemberService(uow=uow)

def category_service_factory():
    """Fábrica padrão para uso em produção (com SQLAlchemy real)."""
    from infrastructure.database.database import SessionLocal
    from infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
    from application.services.category_service import CategoryService

    uow = SQLAlchemyUnitOfWork(SessionLocal)
    return CategoryService(uow=uow)

def dashboard_service_factory():
    """Fábrica padrão para uso em produção (com SQLAlchemy real)."""
    from infrastructure.database.database import SessionLocal
    from infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
    from application.services.dashboard_service import DashboardService

    uow = SQLAlchemyUnitOfWork(SessionLocal)
    return DashboardService(uow=uow)


# --- Identidade e acesso ---

def _security_settings():
    from application.security_settings import SecuritySettings

    config = current_app.config
    return SecuritySettings(
        invitation_ttl=timedelta(hours=config["INVITATION_TTL_HOURS"]),
        recovery_ttl=timedelta(minutes=config["RECOVERY_TTL_MINUTES"]),
        max_code_attempts=config["MAX_CODE_ATTEMPTS"],
    )

def _access_manager():
    from application.services.access_manager import AccessManager
    from interface.web.link_builder import FlaskLinkBuilder

    extensions = current_app.extensions
    return AccessManager(
        hasher=extensions["password_hasher"],
        email_sender=extensions["email_sender"],
        link_builder=FlaskLinkBuilder(current_app.config.get("APP_BASE_URL")),
        settings=_security_settings(),
    )

def _identity_uow():
    from infrastructure.database.database import SessionLocal
    from infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork

    return SQLAlchemyUnitOfWork(SessionLocal)

def user_service_factory():
    """Fábrica padrão para uso em produção (com SQLAlchemy real)."""
    from application.services.user_service import UserService

    return UserService(
        uow=_identity_uow(), password_hasher=current_app.extensions["password_hasher"], access_manager=_access_manager(),
    )

def auth_service_factory():
    """Fábrica padrão para uso em produção (com SQLAlchemy real)."""
    from application.services.auth_service import AuthService

    return AuthService(
        uow=_identity_uow(),
        password_hasher=current_app.extensions["password_hasher"],
        access_manager=_access_manager(),
        secret_key=current_app.config["SECRET_KEY"],
    )

def credential_service_factory():
    """Fábrica padrão para uso em produção (com SQLAlchemy real)."""
    from application.services.credential_service import CredentialService

    return CredentialService(
        uow=_identity_uow(),
        password_hasher=current_app.extensions["password_hasher"],
        access_manager=_access_manager(),
        settings=_security_settings(),
    )

from application.dtos.shared_dtos import ALLOWED_PAGE_SIZES
from interface.web.labels import family_label, highlight, highlight_label, role_label, status_label


def create_app(test_config=None):
    """Factory Pattern: Cria e configura uma instância da aplicação Flask."""

    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="interface/web/templates",
        static_folder="interface/web/static",
    )

    # 1. Carrega as Configurações
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # Valida (uma única vez) SECRET_KEY, APP_ENV, AUTH_ENABLED e as regras de produção. Falha fechado.
    validate_security_config(app.config)

    # 2. Inicializa a Infraestrutura (Banco de Dados) de forma explícita
    init_db(app)

    from infrastructure.email.log_email_sender import LogEmailSender
    from infrastructure.security.password_hasher import Argon2PasswordHasher

    app.extensions["password_hasher"] = Argon2PasswordHasher(app.config["PASSWORD_HASH_PROFILE"])
    app.extensions["email_sender"] = LogEmailSender()

    app.jinja_env.filters['family_label'] = family_label
    app.jinja_env.filters['highlight'] = highlight
    app.jinja_env.filters['highlight_label'] = highlight_label
    app.jinja_env.filters['role_label'] = role_label
    app.jinja_env.filters['status_label'] = status_label
    app.jinja_env.globals['page_sizes'] = ALLOWED_PAGE_SIZES

    # Injeção de dependência via Factory.
    # Em produção, usa o banco real. Em testes, será sobrescrito.
    app.family_service_factory = family_service_factory
    app.family_cost_center_service_factory = family_cost_center_service_factory
    app.member_service_factory = member_service_factory
    app.category_service_factory = category_service_factory
    app.dashboard_service_factory = dashboard_service_factory
    app.user_service_factory = user_service_factory
    app.auth_service_factory = auth_service_factory
    app.credential_service_factory = credential_service_factory

    # Segurança da camada web: sessão, proteção de rotas (negar por padrão), CSRF, limites e cabeçalhos.
    from interface.web.security import init_security
    init_security(app)

    # Registro das Rotas (Blueprints)
    from interface.web.routes.auth_routes import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from interface.web.routes.dashboard_routes import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)

    from interface.web.routes.family_routes import bp as family_bp
    app.register_blueprint(family_bp, url_prefix='/family')

    from interface.web.routes.family_cost_center_routes import bp as family_cost_center_bp
    app.register_blueprint(family_cost_center_bp, url_prefix='/cost-center')

    from interface.web.routes.member_routes import bp as member_bp
    app.register_blueprint(member_bp, url_prefix='/member')

    from interface.web.routes.category_routes import bp as category_bp
    app.register_blueprint(category_bp, url_prefix='/category')

    from interface.web.routes.user_routes import bp as user_bp
    app.register_blueprint(user_bp, url_prefix='/user')

    # Comandos de linha de comando (flask <comando>)
    from interface.cli.category_commands import register_category_commands
    register_category_commands(app)

    from interface.cli.user_commands import register_user_commands
    register_user_commands(app)

    if not app.config["AUTH_ENABLED"]:
        app.logger.warning(
            "PROTEÇÃO DE ROTAS DESLIGADA (AUTH_ENABLED=false, APP_ENV=development): a aplicação autentica "
            "sozinha como '%s'. Use só em desenvolvimento.", app.config["DEV_AUTO_LOGIN_USERNAME"],
        )

    return app

if __name__ == "__main__":
    # Quando rodar pelo terminal direto
    app = create_app()
    app.run(debug=True)
