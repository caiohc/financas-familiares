from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Criamos a Fábrica de Sessões pura. Sem mágicas atreladas a Threads ou ao Flask.
SessionLocal = sessionmaker(autocommit=False, autoflush=False)

def init_db(app):
    """Inicializa o banco de dados definindo o Engine."""
    database_uri = app.config.get("SQLALCHEMY_DATABASE_URI")

    if not database_uri:
        raise RuntimeError(
            "DATABASE_URI não definida."
        )

    # 1. Cria o Engine a partir da URL fornecida (seja PostgreSQL ou SQLite)
    engine = create_engine(
        database_uri,
        echo=app.config.get("DEBUG", False),
        connect_args={"check_same_thread": False} if "sqlite" in database_uri else {}
    )

    # 2. Conecta a nossa fábrica local ao Engine recém-criado
    SessionLocal.configure(bind=engine)
    
    # Observação: Não precisamos mais do @app.teardown_appcontext.
    # Nossa arquitetura usando Unit of Work + DTOs garante que a sessão
    # seja fechada de forma determinística no fim do bloco 'with', sem
    # acoplamento com o ciclo de vida da requisição HTTP do Flask.
