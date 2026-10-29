import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    """Configurações centrais da aplicação lidas do ambiente."""
    
    # 1. URI do Banco de Dados
    # Em produção, a variável deve vir completa via dotenv (ex: postgresql://...).
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")

    # Chave usada para assinar o cookie de sessão (ex: flash messages).
    SECRET_KEY = os.getenv("SECRET_KEY")

    # JSON com as categorias padrão, usado pelo comando `flask seed-categories`.
    CATEGORIES_PATH = os.getenv(
        "CATEGORIES_PATH", str(Path(__file__).parent / "resources" / "default_categories.json")
    )

    # 2. Outras configurações de infraestrutura
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "t")
