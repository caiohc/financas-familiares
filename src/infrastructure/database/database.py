from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Criamos o Registro de Sessões (Session Registry) vazio por enquanto.
# Ele será preenchido apenas quando a aplicação inicializar de verdade.
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False))

def init_db(app):
    """Inicializa o banco de dados amarrando o SQLAlchemy ao ciclo de vida do Flask."""
    database_uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    
    # Fallback Elegante: Se nenhuma URI foi definida, usamos a convenção nativa do Flask
    if not database_uri:
        import os
        # O Flask já sabe onde fica a pasta instance absoluta do projeto
        os.makedirs(app.instance_path, exist_ok=True) 
        db_path = os.path.join(app.instance_path, "app.db")
        database_uri = f"sqlite:///{db_path}"
        # Salva de volta nas configurações (útil para logs/debug)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri

    # 1. Cria o Engine a partir da URL fornecida (seja PostgreSQL ou SQLite)
    engine = create_engine(
        database_uri,
        echo=app.config.get("DEBUG", False),
        connect_args={"check_same_thread": False} if "sqlite" in database_uri else {}
    )

    # 2. Conecta a nossa fábrica local ao Engine recém-criado
    SessionLocal.configure(bind=engine)

    # 3. Garante que, ao fim de cada requisição Web, a Sessão seja fechada limpa da memória
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        SessionLocal.remove()
