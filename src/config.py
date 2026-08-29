import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    """Configurações centrais da aplicação lidas do ambiente."""
    
    # 1. URI do Banco de Dados 
    # Em produção, a variável deve vir completa via dotenv (ex: postgresql://...).
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    
    # 2. Outras configurações de infraestrutura
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "t")
