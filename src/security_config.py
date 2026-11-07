"""
Validação da configuração de segurança, feita UMA vez, na criação da aplicação.

Falha fechado: qualquer valor ausente ou inválido impede a subida, com a lista de problemas.
Depois da validação, as demais camadas só leem a configuração já normalizada.
"""
from datetime import timedelta
from typing import MutableMapping

VALID_ENVIRONMENTS = ("development", "production")
VALID_EMAIL_BACKENDS = ("log", "smtp")
_TRUE = {"true", "1", "t", "yes"}
_FALSE = {"false", "0", "f", "no"}


class ConfigurationError(RuntimeError):
    """A configuração de segurança é inválida: a aplicação não deve subir."""


def _parse_bool(value) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower() if value is not None else ""
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    return None


def validate_security_config(config: MutableMapping) -> None:
    """Valida e normaliza `config` (AUTH_ENABLED vira bool; define o tempo de vida da sessão)."""
    problems: list[str] = []

    if not config.get("SECRET_KEY"):
        raise ConfigurationError("SECRET_KEY não definida. Configure-a no arquivo .env.")

    environment = config.get("APP_ENV")
    if environment not in VALID_ENVIRONMENTS:
        problems.append(
            "APP_ENV não definida ou inválida: informe 'development' ou 'production' (sem valor padrão)."
        )

    auth_enabled = _parse_bool(config.get("AUTH_ENABLED"))
    if auth_enabled is None:
        problems.append("AUTH_ENABLED não definida ou inválida: informe 'true' ou 'false' (sem valor padrão).")

    email_backend = config.get("EMAIL_BACKEND")
    if email_backend not in VALID_EMAIL_BACKENDS:
        problems.append("EMAIL_BACKEND inválido: use 'log' (desenvolvimento) ou 'smtp'.")
    elif email_backend == "smtp":
        problems.append("EMAIL_BACKEND=smtp ainda não está implementado: use 'log' em desenvolvimento.")

    if auth_enabled is False:
        if environment != "development":
            problems.append("A proteção de rotas só pode ser desligada (AUTH_ENABLED=false) com APP_ENV=development.")
        if not config.get("DEV_AUTO_LOGIN_USERNAME"):
            problems.append(
                "Com AUTH_ENABLED=false, informe DEV_AUTO_LOGIN_USERNAME: o usuário como o qual a aplicação "
                "autentica sozinha em desenvolvimento."
            )

    if environment == "production":
        if auth_enabled is not True:
            problems.append("Em produção, AUTH_ENABLED deve ser 'true'.")
        if config.get("DEBUG"):
            problems.append("Em produção, o modo DEBUG deve estar desligado (FLASK_DEBUG).")
        if len(str(config.get("SECRET_KEY"))) < config.get("SECRET_KEY_MIN_LENGTH", 32):
            problems.append(
                f"Em produção, a SECRET_KEY precisa ter pelo menos {config.get('SECRET_KEY_MIN_LENGTH', 32)} caracteres."
            )
        if not config.get("SESSION_COOKIE_SECURE"):
            problems.append("Em produção, SESSION_COOKIE_SECURE deve ser 'true' (cookie só por HTTPS).")
        if email_backend != "smtp":
            problems.append("Em produção, EMAIL_BACKEND deve ser 'smtp'.")
        base_url = str(config.get("APP_BASE_URL") or "")
        if not base_url.startswith("https://"):
            problems.append("Em produção, APP_BASE_URL deve ser o endereço público da aplicação, começando por https://.")

    if problems:
        raise ConfigurationError(
            "Configuração de segurança inválida:\n- " + "\n- ".join(problems)
        )

    config["AUTH_ENABLED"] = bool(auth_enabled)
    config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=config.get("SESSION_IDLE_TIMEOUT_MINUTES", 30))
