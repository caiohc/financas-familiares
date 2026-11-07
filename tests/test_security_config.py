"""A aplicação só sobe com a configuração de segurança válida (falha fechada) e a normaliza."""
from datetime import timedelta

import pytest

from security_config import ConfigurationError, validate_security_config

STRONG_KEY = "k" * 40


def _dev(**overrides) -> dict:
    config = {
        "SECRET_KEY": STRONG_KEY, "APP_ENV": "development", "AUTH_ENABLED": "true", "EMAIL_BACKEND": "log",
        "DEBUG": False, "SESSION_COOKIE_SECURE": False, "APP_BASE_URL": None, "DEV_AUTO_LOGIN_USERNAME": None,
        "SESSION_IDLE_TIMEOUT_MINUTES": 30, "SECRET_KEY_MIN_LENGTH": 32,
    }
    config.update(overrides)
    return config


def _production(**overrides) -> dict:
    """Uma configuração de produção válida, exceto pelo EMAIL_BACKEND=smtp, que ainda não existe."""
    config = _dev(
        APP_ENV="production", AUTH_ENABLED="true", EMAIL_BACKEND="smtp", SESSION_COOKIE_SECURE=True,
        APP_BASE_URL="https://financas.example.com",
    )
    config.update(overrides)
    return config


def _problems(config: dict) -> str:
    with pytest.raises(ConfigurationError) as exc:
        validate_security_config(config)
    return str(exc.value)


# --- Valores obrigatórios e sem padrão ---

def test_a_valid_development_config_is_accepted_and_normalized():
    config = _dev()

    validate_security_config(config)

    assert config["AUTH_ENABLED"] is True
    assert config["PERMANENT_SESSION_LIFETIME"] == timedelta(minutes=30)


def test_the_secret_key_is_required():
    assert "SECRET_KEY não definida" in _problems(_dev(SECRET_KEY=None))
    assert "SECRET_KEY não definida" in _problems(_dev(SECRET_KEY=""))


@pytest.mark.parametrize("value", [None, "", "dev", "Development", "prod", "staging", "test", 1])
def test_app_env_is_required_and_only_development_or_production(value):
    assert "APP_ENV" in _problems(_dev(APP_ENV=value))


@pytest.mark.parametrize("value", [None, "", "talvez", "2", "sim, claro"])
def test_auth_enabled_is_required_and_must_be_a_boolean_word(value):
    assert "AUTH_ENABLED" in _problems(_dev(AUTH_ENABLED=value))


@pytest.mark.parametrize("value, expected", [
    ("true", True), ("True", True), ("1", True), ("t", True), (True, True),
    ("false", False), ("FALSE", False), ("0", False), ("f", False), (False, False),
])
def test_auth_enabled_accepts_the_usual_boolean_spellings(value, expected):
    config = _dev(AUTH_ENABLED=value, DEV_AUTO_LOGIN_USERNAME="dev")
    validate_security_config(config)
    assert config["AUTH_ENABLED"] is expected


def test_several_problems_are_reported_together():
    message = _problems(_dev(APP_ENV=None, AUTH_ENABLED=None))
    assert "APP_ENV" in message and "AUTH_ENABLED" in message


# --- Proteção desligada: só em desenvolvimento, e com usuário de desenvolvimento ---

def test_protection_off_in_development_needs_a_dev_user():
    assert "DEV_AUTO_LOGIN_USERNAME" in _problems(_dev(AUTH_ENABLED="false"))


def test_protection_off_in_development_with_a_dev_user_is_accepted():
    config = _dev(AUTH_ENABLED="false", DEV_AUTO_LOGIN_USERNAME="caio")
    validate_security_config(config)
    assert config["AUTH_ENABLED"] is False


def test_protection_can_never_be_off_in_production():
    message = _problems(_production(AUTH_ENABLED="false", DEV_AUTO_LOGIN_USERNAME="caio"))
    assert "só pode ser desligada" in message and "Em produção, AUTH_ENABLED deve ser 'true'" in message


def test_the_dev_user_alone_does_not_turn_protection_off():
    config = _dev(AUTH_ENABLED="true", DEV_AUTO_LOGIN_USERNAME="caio")
    validate_security_config(config)
    assert config["AUTH_ENABLED"] is True


# --- E-mail ---

def test_log_email_backend_is_accepted_in_development():
    validate_security_config(_dev(EMAIL_BACKEND="log"))


@pytest.mark.parametrize("backend", [None, "", "console", "sendgrid"])
def test_unknown_email_backend_is_rejected(backend):
    assert "EMAIL_BACKEND inválido" in _problems(_dev(EMAIL_BACKEND=backend))


def test_smtp_is_not_implemented_yet_so_the_app_will_not_start_with_it():
    assert "ainda não está implementado" in _problems(_dev(EMAIL_BACKEND="smtp"))
    assert "ainda não está implementado" in _problems(_production())


# --- Produção: cada exigência, uma por vez ---

def test_production_with_everything_right_fails_only_because_smtp_is_not_implemented():
    message = _problems(_production())
    assert message.count("\n- ") == 1 and "smtp ainda não está implementado" in message


@pytest.mark.parametrize("overrides, fragment", [
    ({"DEBUG": True}, "modo DEBUG deve estar desligado"),
    ({"SECRET_KEY": "curta"}, "SECRET_KEY precisa ter pelo menos 32"),
    ({"SECRET_KEY": "k" * 31}, "SECRET_KEY precisa ter pelo menos 32"),
    ({"SESSION_COOKIE_SECURE": False}, "SESSION_COOKIE_SECURE"),
    ({"EMAIL_BACKEND": "log"}, "EMAIL_BACKEND deve ser 'smtp'"),
    ({"APP_BASE_URL": None}, "APP_BASE_URL"),
    ({"APP_BASE_URL": "http://financas.example.com"}, "APP_BASE_URL"),
    ({"APP_BASE_URL": "financas.example.com"}, "APP_BASE_URL"),
])
def test_production_refuses_each_unsafe_setting(overrides, fragment):
    assert fragment in _problems(_production(**overrides))


def test_a_32_character_secret_key_is_enough_in_production():
    message = _problems(_production(SECRET_KEY="k" * 32))
    assert "SECRET_KEY" not in message


def test_production_requires_https_for_the_public_url():
    assert "https://" in _problems(_production(APP_BASE_URL="http://localhost:5000"))


def test_debug_is_free_in_development():
    validate_security_config(_dev(DEBUG=True))


def test_a_short_secret_key_is_tolerated_in_development_only():
    validate_security_config(_dev(SECRET_KEY="curta"))
    assert "SECRET_KEY" in _problems(_production(SECRET_KEY="curta"))


# --- Integração com create_app: a aplicação de fato recusa subir ---

def test_create_app_refuses_to_start_without_app_env(tmp_path):
    from app import create_app
    from support import BASE_APP_CONFIG

    with pytest.raises(ConfigurationError, match="APP_ENV"):
        create_app({**BASE_APP_CONFIG, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'x.db'}", "APP_ENV": None})


def test_create_app_refuses_to_start_without_auth_enabled(tmp_path):
    from app import create_app
    from support import BASE_APP_CONFIG

    with pytest.raises(ConfigurationError, match="AUTH_ENABLED"):
        create_app({**BASE_APP_CONFIG, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'x.db'}", "AUTH_ENABLED": None})


def test_create_app_refuses_protection_off_in_production(tmp_path):
    from app import create_app
    from support import BASE_APP_CONFIG

    with pytest.raises(ConfigurationError, match="só pode ser desligada"):
        create_app({
            **BASE_APP_CONFIG, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'x.db'}",
            "APP_ENV": "production", "AUTH_ENABLED": False,
        })
