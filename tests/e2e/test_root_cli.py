"""
Comandos do root pela aplicação real: avisos claros em create-root (root já existe, nome ou e-mail em uso),
reset-root-password e change-root-email. Complementa tests/e2e/test_user_wiring.py.
"""
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.identity.entities import Role
from infrastructure.database.models import UserModel
from support import STRONG_PASSWORD, create_test_app, insert_user

PASSWORD = "senha-do-root-123"
OTHER = "outra-senha-do-root-456"
PERSONAL_EMAIL = "caio.pessoal@example.com"


@pytest.fixture
def app(tmp_path):
    """Banco com uma conta pessoal já cadastrada (como a do usuário real) e nenhum root."""
    app = create_test_app(tmp_path, AUTH_ENABLED=True, with_dev_user=False)
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    with sessionmaker(bind=engine)() as session:
        from infrastructure.database.models import FamilyModel
        import uuid
        family = FamilyModel(id=str(uuid.uuid4()), name="Família")
        session.add(family)
        session.commit()
        insert_user(session, role=Role.FAMILY_ADMIN, username="caiohc", email=PERSONAL_EMAIL, family_id=uuid.UUID(family.id))
    engine.dispose()
    return app


def _run(app, *args, input_text=""):
    return app.test_cli_runner().invoke(args=list(args), input=input_text)


def _root(app):
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    with sessionmaker(bind=engine)() as session:
        row = session.query(UserModel).filter(UserModel.role == Role.ROOT).first()
        session.expunge_all()
    engine.dispose()
    return row


def _create_root(app, username="root", email="root@example.com"):
    result = _run(app, "create-root", "--username", username, "--email", email, input_text=f"{PASSWORD}\n{PASSWORD}\n")
    assert result.exit_code == 0, result.output
    return result


def _login(app, who, password=PASSWORD):
    return app.test_client().post("/auth/authenticate", data={"identifier": who, "password": password}).status_code


# ---------------------------------------------------------------------------
# create-root: o root já existe
# ---------------------------------------------------------------------------

def test_a_second_root_is_refused_with_a_clear_message_that_reveals_nothing_about_the_existing_one(app):
    _create_root(app)

    result = _run(app, "create-root")                      # sem opções e sem nenhuma entrada

    assert result.exit_code == 1
    assert 'Já existe um usuário root.' in result.output
    assert "único root" in result.output and "segundo não pode ser criado" in result.output
    assert '"root"' not in result.output and "root@example.com" not in result.output


def test_the_refusal_points_to_the_commands_that_change_the_password_and_the_email(app):
    _create_root(app)

    output = _run(app, "create-root").output

    assert "flask reset-root-password" in output and "flask change-root-email" in output


def test_the_refusal_comes_before_any_question_is_asked(app):
    _create_root(app)

    output = _run(app, "create-root").output

    assert "Nome de usuário" not in output and "E-mail:" not in output and "Senha" not in output


def test_the_refusal_with_options_changes_nothing(app):
    _create_root(app)

    result = _run(app, "create-root", "--username", "outro", "--email", "outro@example.com", input_text=f"{PASSWORD}\n{PASSWORD}\n")

    assert result.exit_code == 1
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    with sessionmaker(bind=engine)() as session:
        assert session.query(UserModel).filter(UserModel.role == Role.ROOT).count() == 1
        assert session.query(UserModel).filter(UserModel.username == "outro").count() == 0
    engine.dispose()


# ---------------------------------------------------------------------------
# create-root: nome de usuário ou e-mail já em uso
# ---------------------------------------------------------------------------

def test_an_email_already_used_by_another_account_is_explained_without_revealing_the_owner(app):
    result = _run(app, "create-root", "--username", "root", "--email", PERSONAL_EMAIL, input_text=f"{PASSWORD}\n{PASSWORD}\n")

    assert result.exit_code == 1
    assert f'O e-mail "{PERSONAL_EMAIL}" já está cadastrado no sistema' in result.output
    assert "caiohc" not in result.output
    assert _root(app) is None


def test_the_email_conflict_explains_that_the_root_is_not_a_person_and_needs_its_own_email(app):
    output = _run(app, "create-root", "--username", "root", "--email", PERSONAL_EMAIL).output

    assert "O root não representa uma pessoa" in output and "e-mail só dele" in output


def test_an_email_conflict_does_not_ask_for_the_password_first(app):
    output = _run(app, "create-root", "--username", "root", "--email", PERSONAL_EMAIL).output

    assert "Senha" not in output and "Repeat for confirmation" not in output


def test_the_email_conflict_ignores_case(app):
    result = _run(app, "create-root", "--username", "root", "--email", PERSONAL_EMAIL.upper())

    assert result.exit_code == 1 and "já está cadastrado no sistema" in result.output


def test_a_username_already_used_is_explained(app):
    result = _run(app, "create-root", "--username", "CaioHC", "--email", "root@example.com")

    assert result.exit_code == 1
    assert 'O nome de usuário "CaioHC" já está cadastrado no sistema' in result.output
    assert "Escolha outro nome de usuário" in result.output
    assert _root(app) is None


def test_prompted_values_in_conflict_are_asked_again_until_valid(app):
    """Quem digita (não passa opção) tem outra chance: o erro é explicado e a pergunta se repete."""
    typed = "\n".join([
        "caiohc",                 # nome em uso
        "root",                   # nome livre
        PERSONAL_EMAIL,           # e-mail em uso
        "nao-e-email",            # e-mail inválido
        "root@example.com",       # e-mail livre
        PASSWORD, PASSWORD,
    ]) + "\n"

    result = _run(app, "create-root", input_text=typed)

    assert result.exit_code == 0, result.output
    assert 'já está cadastrado no sistema' in result.output and 'já está cadastrado no sistema' in result.output
    assert "e-mail válido" in result.output and 'Usuário root "root" criado' in result.output
    root = _root(app)
    assert (root.username, root.email) == ("root", "root@example.com")


def test_a_weak_password_typed_at_the_prompt_is_explained_and_asked_again(app):
    result = _run(app, "create-root", "--username", "root", "--email", "root@example.com",
                  input_text=f"curta\ncurta\n{PASSWORD}\n{PASSWORD}\n")

    assert result.exit_code == 0, result.output
    assert "pelo menos 8 caracteres" in result.output
    assert _login(app, "root") == 302


def test_the_error_lines_are_marked_and_have_no_traceback(app):
    output = _run(app, "create-root", "--username", "root", "--email", PERSONAL_EMAIL).output

    assert output.lstrip().startswith("✗") and "Traceback" not in output and "IntegrityError" not in output


def test_the_success_message_is_clear(app):
    output = _create_root(app).output

    assert '✓ Usuário root "root" criado.' in output


# ---------------------------------------------------------------------------
# O aviso não pode ficar enterrado em SQL (FLASK_DEBUG ligado)
# ---------------------------------------------------------------------------

def test_debug_mode_no_longer_turns_on_the_sql_echo(tmp_path):
    from infrastructure.database.database import SessionLocal

    create_test_app(tmp_path, DEBUG=True)

    assert SessionLocal.kw["bind"].echo is False


def test_the_sql_echo_is_an_explicit_opt_in(tmp_path):
    from infrastructure.database.database import SessionLocal

    create_test_app(tmp_path, SQL_ECHO=True)
    assert SessionLocal.kw["bind"].echo is True

    other_folder = tmp_path / "sem-eco"
    other_folder.mkdir()
    create_test_app(other_folder)
    assert SessionLocal.kw["bind"].echo is False


# ---------------------------------------------------------------------------
# reset-root-password
# ---------------------------------------------------------------------------

def test_reset_root_password_asks_again_after_a_weak_password(app):
    _create_root(app)

    result = _run(app, "reset-root-password", input_text=f"curta\ncurta\n{OTHER}\n{OTHER}\n")

    assert result.exit_code == 0, result.output
    assert "pelo menos 8 caracteres" in result.output and "redefinida" in result.output
    assert _login(app, "root", OTHER) == 302 and _login(app, "root", PASSWORD) == 401


def test_reset_root_password_without_a_root_says_how_to_create_one(app):
    result = _run(app, "reset-root-password", input_text=f"{OTHER}\n{OTHER}\n")

    assert result.exit_code == 1 and "Ainda não existe usuário root" in result.output and "flask create-root" in result.output
    assert "Nova senha" not in result.output          # nem pergunta a senha


def test_reset_root_password_with_the_option_and_a_weak_value_fails(app):
    _create_root(app)

    result = _run(app, "reset-root-password", "--password", "curta")

    assert result.exit_code == 1 and "pelo menos 8 caracteres" in result.output
    assert _login(app, "root") == 302


# ---------------------------------------------------------------------------
# change-root-email
# ---------------------------------------------------------------------------

def test_change_root_email_with_the_option(app):
    _create_root(app)

    result = _run(app, "change-root-email", "--email", "novo.root@example.com")

    assert result.exit_code == 0, result.output
    assert "E-mail atual do root" in result.output and "root@example.com" in result.output
    assert '✓ E-mail do root "root" alterado para novo.root@example.com.' in result.output
    assert _root(app).email == "novo.root@example.com"


def test_change_root_email_interactively_confirms_the_address(app):
    _create_root(app)

    result = _run(app, "change-root-email", input_text="novo.root@example.com\nnovo.root@example.com\n")

    assert result.exit_code == 0, result.output
    assert _root(app).email == "novo.root@example.com"


def test_a_mismatching_confirmation_asks_for_both_fields_again(app):
    _create_root(app)

    result = _run(app, "change-root-email",
                  input_text="digitado.errado@example.com\noutro@example.com\ncerto@example.com\ncerto@example.com\n")

    assert result.exit_code == 0, result.output
    assert "e-mails informados não conferem" in result.output
    assert _root(app).email == "certo@example.com"


def test_the_new_email_cannot_be_another_accounts_and_the_owner_is_not_revealed(app):
    _create_root(app)

    result = _run(app, "change-root-email", "--email", PERSONAL_EMAIL)

    assert result.exit_code == 1
    assert f'O e-mail "{PERSONAL_EMAIL}" já está cadastrado no sistema' in result.output
    assert "caiohc" not in result.output
    assert _root(app).email == "root@example.com"


def test_the_new_email_equal_to_the_current_is_explained(app):
    _create_root(app)

    for typed in ("root@example.com", "ROOT@Example.com"):
        result = _run(app, "change-root-email", "--email", typed)
        assert result.exit_code == 1 and "igual ao atual" in result.output


@pytest.mark.parametrize("bad", ["nao-e-email", "a@b", "@example.com", ""])
def test_an_invalid_new_email_is_refused(app, bad):
    _create_root(app)

    result = _run(app, "change-root-email", "--email", bad)

    assert result.exit_code == 1 and "e-mail" in result.output.lower()
    assert _root(app).email == "root@example.com"


def test_change_root_email_without_a_root_says_how_to_create_one(app):
    result = _run(app, "change-root-email", "--email", "x@example.com")

    assert result.exit_code == 1 and "Ainda não existe usuário root" in result.output and "flask create-root" in result.output


def test_the_new_email_works_for_login_and_the_old_one_does_not(app):
    _create_root(app)

    _run(app, "change-root-email", "--email", "novo.root@example.com")

    assert _login(app, "novo.root@example.com") == 302
    assert _login(app, "root@example.com") == 401
    assert _login(app, "root") == 302                      # o nome de usuário não mudou


def test_changing_the_email_does_not_touch_the_password_nor_the_open_session(app):
    _create_root(app)
    client = app.test_client()
    client.post("/auth/authenticate", data={"identifier": "root", "password": PASSWORD})
    hash_before = _root(app).password_hash

    _run(app, "change-root-email", "--email", "novo.root@example.com")

    assert _root(app).password_hash == hash_before
    assert client.get("/").status_code == 200              # a sessão depende da senha, não do e-mail


def test_the_cli_changes_the_roots_email_even_though_administrators_cannot(app):
    """A trava pós-ativação vale para a edição administrativa; a CLI, no servidor, é o canal legítimo do root."""
    _create_root(app)
    assert _root(app).activated_at is not None

    assert _run(app, "change-root-email", "--email", "novo.root@example.com").exit_code == 0


def test_change_root_email_does_not_touch_other_accounts(app):
    _create_root(app)
    _run(app, "change-root-email", "--email", "novo.root@example.com")

    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    with sessionmaker(bind=engine)() as session:
        assert session.query(UserModel).filter(UserModel.username == "caiohc").one().email == PERSONAL_EMAIL
    engine.dispose()
    assert _login(app, "caiohc", STRONG_PASSWORD) == 302


# ---------------------------------------------------------------------------
# Ajuda
# ---------------------------------------------------------------------------

def test_the_three_root_commands_are_listed_with_a_description(app):
    output = _run(app, "--help").output

    for command in ("create-root", "reset-root-password", "change-root-email"):
        assert re.search(rf"{command}\s+\S", output), command


