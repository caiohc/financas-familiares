from flask import Flask
from config import Config
from infrastructure.database.database import init_db

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

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY não definida. Configure-a no arquivo .env.")

    # 2. Inicializa a Infraestrutura (Banco de Dados) de forma explícita
    init_db(app)
    
    # Injeção de dependência via Factory.
    # Em produção, usa o banco real. Em testes, será sobrescrito.
    app.family_service_factory = family_service_factory
    app.family_cost_center_service_factory = family_cost_center_service_factory
    app.member_service_factory = member_service_factory
    app.category_service_factory = category_service_factory
    app.dashboard_service_factory = dashboard_service_factory

    # Registro das Rotas (Blueprints)
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

    # Comandos de linha de comando (flask <comando>)
    from interface.cli.category_commands import register_category_commands
    register_category_commands(app)

    return app

if __name__ == "__main__":
    # Quando rodar pelo terminal direto
    app = create_app()
    app.run(debug=True)
