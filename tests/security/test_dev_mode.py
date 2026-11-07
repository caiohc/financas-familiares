"""
Modo de desenvolvimento (AUTH_ENABLED=false): a aplicação autentica sozinha como um usuário configurado.
A proteção real (papéis, escopo) continua valendo, e o cliente não consegue trocar de usuário.
"""
import logging
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.identity.entities import Role
from support import DEV_USER, create_test_app, insert_user


def _dev_app(tmp_path, **config):
    return create_test_app(tmp_path, **config)          # AUTH_ENABLED=False e o usuário "dev-admin" do auxiliar


def _insert(app, **kwargs):
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    with sessionmaker(bind=engine)() as session:
        user_id = insert_user(session, **kwargs)
    engine.dispose()
    return user_id


def test_requests_are_authenticated_as_the_configured_user(tmp_path):
    client = _dev_app(tmp_path).test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert DEV_USER in response.get_data(as_text=True)


def test_every_page_is_reachable_without_logging_in(tmp_path):
    client = _dev_app(tmp_path).test_client()

    for url in ("/", "/family/list", "/member/list", "/cost-center/list", "/category/list", "/user/list"):
        assert client.get(url).status_code == 200, url


def test_a_banner_warns_that_protection_is_off(tmp_path):
    html = _dev_app(tmp_path).test_client().get("/").get_data(as_text=True)

    assert "Proteção de rotas DESLIGADA" in html and "AUTH_ENABLED=false" in html
    assert f"<strong>{DEV_USER}</strong>" in html


def test_there_is_no_banner_when_protection_is_on(world):
    world.add_user("admin", Role.SYSTEM_ADMIN)

    assert "DESLIGADA" not in world.logged("admin").get("/").get_data(as_text=True)


def test_a_startup_warning_is_logged_when_protection_is_off(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        _dev_app(tmp_path)

    assert any("PROTEÇÃO DE ROTAS DESLIGADA" in r.getMessage() and DEV_USER in r.getMessage() for r in caplog.records)


def test_no_startup_warning_when_protection_is_on(make_world, caplog):
    with caplog.at_level(logging.WARNING):
        make_world()

    assert not any("DESLIGADA" in r.getMessage() for r in caplog.records)


# --- O cliente não escolhe quem é ---

@pytest.mark.parametrize("probe", [
    {"headers": {"X-Dev-User": "root"}}, {"headers": {"X-User": "root"}}, {"headers": {"Authorization": "Bearer root"}},
    {"query_string": {"dev_user": "root", "user": "root", "username": "root"}},
    {"headers": {"Cookie": "dev_user=root; user=root"}},
])
def test_the_client_cannot_switch_to_another_user(tmp_path, probe):
    app = _dev_app(tmp_path)
    _insert(app, role=Role.ROOT, username="root")
    client = app.test_client()

    html = client.get("/", **probe).get_data(as_text=True)

    assert f"<strong>{DEV_USER}</strong>" in html and "Root" not in html.split("<main")[0]


# --- Sem usuário de desenvolvimento válido, ninguém entra ---

def test_without_the_dev_user_in_the_database_everything_asks_for_login(tmp_path):
    client = create_test_app(tmp_path, with_dev_user=False).test_client()

    response = client.get("/")

    assert response.status_code == 302 and response.headers["Location"].startswith("/auth/login")


def test_a_deactivated_dev_user_is_not_logged_in(tmp_path):
    app = create_test_app(tmp_path, with_dev_user=False)
    _insert(app, username=DEV_USER, is_active=False)

    assert app.test_client().get("/").status_code == 302


def test_a_pending_dev_user_is_not_logged_in(tmp_path):
    app = create_test_app(tmp_path, with_dev_user=False)
    _insert(app, username=DEV_USER, password=None, activated=False)

    assert app.test_client().get("/").status_code == 302


def test_a_dev_user_configured_by_a_name_that_does_not_exist_is_not_logged_in(tmp_path):
    client = _dev_app(tmp_path, DEV_AUTO_LOGIN_USERNAME="fantasma").test_client()

    assert client.get("/").status_code == 302


# --- A autorização continua valendo com o usuário de desenvolvimento ---

def test_a_family_user_as_dev_user_cannot_open_the_user_area(tmp_path):
    app = create_test_app(tmp_path, with_dev_user=False, DEV_AUTO_LOGIN_USERNAME="usuario-comum")
    family = uuid.uuid4()
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    with sessionmaker(bind=engine)() as session:
        from infrastructure.database.models import FamilyModel
        session.add(FamilyModel(id=str(family), name="Silva"))
        session.commit()
        insert_user(session, role=Role.FAMILY_USER, username="usuario-comum", family_id=family)
    engine.dispose()
    client = app.test_client()

    assert client.get("/").status_code == 200
    assert client.get("/user/list").status_code == 403
    assert client.get("/user/new").status_code == 403


def test_a_family_admin_as_dev_user_sees_only_its_family(tmp_path):
    app = create_test_app(tmp_path, with_dev_user=False, DEV_AUTO_LOGIN_USERNAME="admin-a")
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    with sessionmaker(bind=engine)() as session:
        from infrastructure.database.models import FamilyModel
        fam_a, fam_b = uuid.uuid4(), uuid.uuid4()
        session.add_all([FamilyModel(id=str(fam_a), name="A"), FamilyModel(id=str(fam_b), name="B")])
        session.commit()
        insert_user(session, role=Role.FAMILY_ADMIN, username="admin-a", family_id=fam_a)
        insert_user(session, role=Role.FAMILY_USER, username="user-a", family_id=fam_a)
        insert_user(session, role=Role.FAMILY_USER, username="user-b", family_id=fam_b)
    engine.dispose()

    html = app.test_client().get("/user/list").get_data(as_text=True)

    assert "user-a" in html and "user-b" not in html


def test_the_dev_user_can_manage_users_as_a_system_admin(tmp_path):
    client = _dev_app(tmp_path).test_client()

    response = client.post("/user/create", data={
        "role": "SYSTEM_ADMIN", "name": "Novo", "username": "novo", "email": "novo@example.com",
        "email_confirmation": "novo@example.com",
    })

    assert response.status_code == 200 and "Código de ativação" in response.get_data(as_text=True)


# --- Os demais controles não dependem do modo ---

def test_csrf_stays_enforced_in_dev_mode_when_enabled(tmp_path):
    client = _dev_app(tmp_path, WTF_CSRF_ENABLED=True).test_client()

    assert client.post("/family/create", data={"name": "Sem token"}).status_code == 400


def test_security_headers_are_present_in_dev_mode(tmp_path):
    headers = _dev_app(tmp_path).test_client().get("/").headers

    assert headers["X-Frame-Options"] == "DENY" and headers["Referrer-Policy"] == "no-referrer"


def test_a_secure_app_never_inherits_the_dev_auto_login_of_another_app_in_the_same_process(tmp_path, make_world):
    """O carregador de auto-login é de UMA aplicação: criar um app de desenvolvimento antes não pode abrir o seguinte."""
    dev_folder = tmp_path / "dev"
    dev_folder.mkdir()
    _dev_app(dev_folder)                                         # app com a proteção desligada, criado ANTES
    secure = make_world(DEV_AUTO_LOGIN_USERNAME=DEV_USER)       # proteção ligada, MESMO nome de usuário de desenvolvimento
    secure.add_user(DEV_USER, Role.SYSTEM_ADMIN)

    response = secure.client().get("/")

    assert response.status_code == 302 and response.headers["Location"].startswith("/auth/login")


def test_the_dev_user_setting_is_ignored_when_protection_is_on(make_world):
    world = make_world(DEV_AUTO_LOGIN_USERNAME=DEV_USER)
    world.add_user(DEV_USER, Role.SYSTEM_ADMIN)

    assert world.client().get("/user/list").status_code == 302
