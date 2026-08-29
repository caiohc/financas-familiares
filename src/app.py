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

def create_app():
    """Factory Pattern: Cria e configura uma instância da aplicação Flask."""
    
    app = Flask(__name__, instance_relative_config=True)
    
    # 1. Carrega as Configurações 
    app.config.from_object(Config)
    
    # 2. Inicializa a Infraestrutura (Banco de Dados) de forma explícita
    init_db(app)
    
    # Injeção de dependência via Factory. 
    # Em produção, usa o banco real. Em testes, será sobrescrito.
    app.family_service_factory = family_service_factory
    
    # Registro das Rotas (Blueprints)
    from interface.web.routes.family_routes import bp as family_bp
    app.register_blueprint(family_bp, url_prefix='/families')
    
    return app

if __name__ == "__main__":
    # Quando rodar pelo terminal direto
    app = create_app()
    app.run(debug=True)
