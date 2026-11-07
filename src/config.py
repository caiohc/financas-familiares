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
    # Desligado por padrão: o depurador interativo permite executar código. Ligue só em desenvolvimento.
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")

    # Eco de todo o SQL no terminal. Separado do DEBUG: ligado junto com ele, enterrava as mensagens dos comandos
    # de CLI (ex.: o aviso de que o root já existe) no meio de centenas de linhas de SQL.
    SQL_ECHO = os.getenv("SQL_ECHO", "False").lower() in ("true", "1", "t")

    # 3. Segurança (ver docs/seguranca_docs.md, Seção 12)
    # Ambiente e proteção de rotas: SEM valor padrão. Se faltarem, a aplicação não sobe (ver security_config.py).
    APP_ENV = os.getenv("APP_ENV")                      # "development" ou "production"
    AUTH_ENABLED = os.getenv("AUTH_ENABLED")            # "true" ou "false" (false só em development)
    # Com AUTH_ENABLED=false, a aplicação autentica sozinha como este usuário (precisa existir e estar ativo).
    DEV_AUTO_LOGIN_USERNAME = os.getenv("DEV_AUTO_LOGIN_USERNAME")

    # Endereço público da aplicação, usado nos links enviados por e-mail. Obrigatório em produção: sem ele os
    # links seriam montados a partir do cabeçalho Host da requisição, que um atacante pode forjar.
    APP_BASE_URL = os.getenv("APP_BASE_URL")

    # "log" (desenvolvimento: escreve a mensagem no log) ou "smtp" (ainda não implementado).
    EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "log")

    # Cookie de sessão: HttpOnly e SameSite=Lax sempre; Secure (só HTTPS) obrigatório em produção.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "t")

    # Prazos decididos. Sessão: 30 minutos sem uso e no máximo 8 horas desde o login.
    SESSION_IDLE_TIMEOUT_MINUTES = 30
    SESSION_ABSOLUTE_TIMEOUT_HOURS = 8
    # Convite de ativação/redefinição: 24 horas. Recuperação de senha: 15 minutos. Tentativas do código: 5.
    INVITATION_TTL_HOURS = 24
    RECOVERY_TTL_MINUTES = 15
    MAX_CODE_ATTEMPTS = 5

    # Em produção a SECRET_KEY precisa ser longa e aleatória (ex.: secrets.token_hex(32)).
    SECRET_KEY_MIN_LENGTH = 32

    # "default" (Argon2id com os parâmetros da biblioteca) ou "test" (leve, só para a suíte de testes).
    PASSWORD_HASH_PROFILE = "default"

    # Limite de tentativas (Flask-Limiter). Em memória: vale por processo; com vários processos use Redis.
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = "memory://"
