import os
from alembic.config import Config
from alembic import command
from config import BASE_DIR

def apply_migrations(db_path: str):
    """Aplica as migrações configuradas ao banco de dados via Alembic."""
    
    # Certifica-se de que o diretório base do banco exista
    db_abs_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(db_abs_path), exist_ok=True)
    
    # Executa a migração programaticamente
    alembic_cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
    
    # Definindo a raiz da pasta alembic
    alembic_cfg.set_main_option("script_location", os.path.join(BASE_DIR, "alembic"))
    
    # Roda o upgrade
    command.upgrade(alembic_cfg, "head")

