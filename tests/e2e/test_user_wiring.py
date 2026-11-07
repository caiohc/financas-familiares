"""Comandos de CLI do root, pela aplicação real: create-root e reset-root-password."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.identity.entities import Role
from infrastructure.database.models import UserModel
from support import create_test_app

PASSWORD = "senha-do-root-123"
OTHER = "outra-senha-do-root-456"


@pytest.fixture
def app(tmp_path):
    # A CLI não depende do login; AUTH_ENABLED=True permite conferir o login do root pela web logo em seguida.
    return create_test_app(tmp_path, AUTH_ENABLED=True, with_dev_user=False)


def _create_root(app, **options):
    args = ["create-root"] + [token for key, value in options.items() for token in (f"--{key}", value)]
    return app.test_cli_runner().invoke(args=args, input=f"{PASSWORD}\n{PASSWORD}\n")


def _row(app):
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    with sessionmaker(bind=engine)() as session:
        row = session.query(UserModel).filter(UserModel.role == Role.ROOT).first()
        session.expunge_all()
    engine.dispose()
    return row


def _web_login(app, username, password):
    return app.test_client().post("/auth/authenticate", data={"identifier": username, "password": password}).status_code


# --- create-root ---

def test_create_root_command_through_the_real_stack(app):
    result = _create_root(app, username="root", email="root@example.com")

    assert result.exit_code == 0, result.output
    assert 'Usuário root "root" criado' in result.output
    row = _row(app)
    assert row.role is Role.ROOT and row.family_id is None and row.name is None
    assert row.is_active is True and row.activated_at is not None
    assert row.password_hash.startswith("$argon2id$")                 # Argon2id, nunca a senha


def test_the_root_created_by_the_cli_can_log_in_through_the_web(app):
    _create_root(app, username="root", email="root@example.com")

    assert _web_login(app, "root", PASSWORD) == 302
    assert _web_login(app, "root", "senha-errada-123") == 401


def test_the_password_is_never_printed_or_stored_in_clear(app):
    result = _create_root(app, username="root", email="root@example.com")

    assert PASSWORD not in result.output
    assert PASSWORD not in _row(app).password_hash


def test_create_root_command_prompts_for_missing_values(app):
    result = app.test_cli_runner().invoke(
        args=["create-root"], input=f"root\nroot@example.com\n{PASSWORD}\n{PASSWORD}\n",
    )

    assert result.exit_code == 0, result.output


def test_create_root_command_refuses_a_second_root(app):
    assert _create_root(app, username="root", email="root@example.com").exit_code == 0

    second = _create_root(app, username="outro", email="outro@example.com")

    assert second.exit_code != 0 and "Já existe um usuário root" in second.output


@pytest.mark.parametrize("password, message", [("curta", "pelo menos 8 caracteres"), ("1234567", "pelo menos 8 caracteres")])
def test_create_root_command_reports_a_weak_password(app, password, message):
    result = app.test_cli_runner().invoke(
        args=["create-root", "--username", "root", "--email", "root@example.com"], input=f"{password}\n{password}\n",
    )

    assert result.exit_code != 0 and message in result.output
    assert _row(app) is None


def test_create_root_command_reports_an_invalid_email(app):
    result = _create_root(app, username="root", email="nao-e-email")

    assert result.exit_code != 0 and "e-mail válido" in result.output
    assert _row(app) is None


def test_create_root_command_refuses_a_mismatching_confirmation(app):
    result = app.test_cli_runner().invoke(
        args=["create-root", "--username", "root", "--email", "root@example.com"],
        input=f"{PASSWORD}\n{OTHER}\n",
    )

    assert result.exit_code != 0
    assert _row(app) is None


# --- reset-root-password ---

def test_reset_root_password_replaces_the_password(app):
    _create_root(app, username="root", email="root@example.com")

    result = app.test_cli_runner().invoke(args=["reset-root-password"], input=f"{OTHER}\n{OTHER}\n")

    assert result.exit_code == 0, result.output
    assert "redefinida" in result.output and OTHER not in result.output
    assert _web_login(app, "root", OTHER) == 302
    assert _web_login(app, "root", PASSWORD) == 401


def test_reset_root_password_ends_the_roots_open_sessions(app):
    _create_root(app, username="root", email="root@example.com")
    client = app.test_client()
    assert client.post("/auth/authenticate", data={"identifier": "root", "password": PASSWORD}).status_code == 302
    assert client.get("/").status_code == 200

    app.test_cli_runner().invoke(args=["reset-root-password"], input=f"{OTHER}\n{OTHER}\n")

    assert client.get("/").status_code == 302


def test_reset_root_password_without_a_root_fails_clearly(app):
    result = app.test_cli_runner().invoke(args=["reset-root-password"], input=f"{OTHER}\n{OTHER}\n")

    assert result.exit_code != 0 and "create-root" in result.output


def test_reset_root_password_rejects_a_weak_password_and_keeps_the_old_one(app):
    _create_root(app, username="root", email="root@example.com")

    result = app.test_cli_runner().invoke(args=["reset-root-password"], input="curta\ncurta\n")

    assert result.exit_code != 0 and "pelo menos 8 caracteres" in result.output
    assert _web_login(app, "root", PASSWORD) == 302


def test_reset_root_password_rejects_a_mismatching_confirmation(app):
    _create_root(app, username="root", email="root@example.com")

    result = app.test_cli_runner().invoke(args=["reset-root-password"], input=f"{OTHER}\nnao-confere-123\n")

    assert result.exit_code != 0
    assert _web_login(app, "root", PASSWORD) == 302


def test_reset_root_password_does_not_touch_other_accounts(app, tmp_path):
    _create_root(app, username="root", email="root@example.com")
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    from support import insert_user
    with sessionmaker(bind=engine)() as session:
        insert_user(session, role=Role.SYSTEM_ADMIN, username="admin")
    engine.dispose()

    app.test_cli_runner().invoke(args=["reset-root-password"], input=f"{OTHER}\n{OTHER}\n")

    assert _web_login(app, "admin", "senha-segura-123") == 302


def test_the_cli_refuses_to_run_without_the_security_configuration(tmp_path):
    from app import create_app
    from security_config import ConfigurationError
    from support import BASE_APP_CONFIG

    with pytest.raises(ConfigurationError):
        create_app({**BASE_APP_CONFIG, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'x.db'}", "APP_ENV": None})
