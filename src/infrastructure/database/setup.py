import os
from yoyo import read_migrations, get_backend
from config import MIGRATIONS_ABS_PATH

def apply_migrations(db_path: str):
    """Aplica as migrações configuradas ao banco de dados."""
    
    # Certifica-se de que o diretório base do banco exista
    db_abs_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(db_abs_path), exist_ok=True)
    
    # Configura o backend do Yoyo para SQLite (normalizando caminhos para o formato de URL)
    db_url = f"sqlite:///{db_abs_path.replace(os.sep, '/')}"
    backend = get_backend(db_url)
    
    # Localiza o diretório de migrações via configuração centralizada
    migrations = read_migrations(str(MIGRATIONS_ABS_PATH))
    
    # Aplica as migrações pendentes
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))

