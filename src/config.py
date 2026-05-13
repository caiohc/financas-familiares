import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Caminho Base do Projeto (Raiz) - Lido obrigatoriamente do .env
PROJECT_ROOT_ENV = os.getenv("PROJECT_ROOT")
if not PROJECT_ROOT_ENV:
    raise RuntimeError("A variável de ambiente 'PROJECT_ROOT' deve estar definida no arquivo .env")

BASE_DIR = Path(PROJECT_ROOT_ENV).resolve()

# Definição dos caminhos lidos do .env ou com valores padrão seguros
DB_PATH = os.getenv("DB_PATH", "app.db")
MIGRATIONS_PATH = os.getenv("MIGRATIONS_PATH", "migrations")
CATEGORIES_PATH = os.getenv("CATEGORIES_PATH", r"src\resources\default_categories.json")

# Converte caminhos relativos em caminhos absolutos baseados na raiz do projeto
def get_absolute_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return BASE_DIR / path

# Atalhos para caminhos absolutos comumente usados
DB_ABS_PATH = get_absolute_path(DB_PATH)
MIGRATIONS_ABS_PATH = get_absolute_path(MIGRATIONS_PATH)
DEFAULT_CATEGORIES_ABS_PATH = get_absolute_path(CATEGORIES_PATH)
