from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, Session
import os
import sys

# Ajustando import do DB_ABS_PATH da raiz @ToDo: refatorar para que seja algo mais limpo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))) 
from config import DB_ABS_PATH

# 1. Configuração do Engine
DATABASE_URL = f"sqlite:///{DB_ABS_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=True,  # Em dev, colocar como True para ver o SQL gerado no console
    connect_args={"check_same_thread": False}
)

from sqlalchemy.orm import scoped_session, sessionmaker

# 2. Configuração da Fábrica de Sessões (Unit of Work)
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal = scoped_session(session_factory)



# 4. Injeção de Dependência (Generator)
# Esta função fornece uma Sessão que será injetada nos repositórios.
def get_db_session() -> Generator[Session, None, None]:
    """Cria uma nova sessão de banco de dados para uma requisição/operação."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
