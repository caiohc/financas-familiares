import pytest
from sqlalchemy import create_engine

from app import create_app
from domain.identity.entities import Role
from infrastructure.database.models import Base
from infrastructure.security.password_hasher import WerkzeugPasswordHasher


@pytest.fixture
def app(tmp_path):
    """App real, fábricas de produção, sem doubles: só confirma o wiring de Usuário em app.py."""
    db_uri = f"sqlite:///{tmp_path / 'wiring_test.db'}"
    setup_engine = create_engine(db_uri)
    Base.metadata.create_all(setup_engine)
    setup_engine.dispose()
    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": db_uri, "SECRET_KEY": "wiring-test-secret"})


def _create_root(app, **options):
    args = ["create-root"] + [token for key, value in options.items() for token in (f"--{key}", value)]
    return app.test_cli_runner().invoke(args=args, input="senha-temporaria\nsenha-temporaria\n")


def test_create_root_command_through_the_real_stack(app):
    result = _create_root(app, username="root", email="root@example.com")

    assert result.exit_code == 0, result.output
    assert 'Usuário root "root" criado' in result.output

    with app.user_service_factory().uow as uow:
        root = uow.users.get_by_username("root")
        assert root.role is Role.ROOT and root.family_id is None and root.name is None
        assert root.must_change_password is True
        assert WerkzeugPasswordHasher().verify("senha-temporaria", root.password_hash)


def test_create_root_command_prompts_for_missing_values(app):
    result = app.test_cli_runner().invoke(
        args=["create-root"], input="root\nroot@example.com\nsenha-temporaria\nsenha-temporaria\n"
    )

    assert result.exit_code == 0, result.output


def test_create_root_command_refuses_a_second_root(app):
    assert _create_root(app, username="root", email="root@example.com").exit_code == 0

    second = _create_root(app, username="outro", email="outro@example.com")

    assert second.exit_code != 0
    assert "Já existe um usuário root" in second.output


def test_create_root_command_reports_invalid_input(app):
    result = app.test_cli_runner().invoke(
        args=["create-root", "--username", "root", "--email", "root@example.com"], input="curta\ncurta\n"
    )

    assert result.exit_code != 0
    assert "pelo menos 8 caracteres" in result.output
