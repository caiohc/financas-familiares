"""Barra de status da autenticação: quem está logado e o botão de sair, no canto superior esquerdo."""
import re
import uuid

import pytest

from application.dtos.dashboard_dtos import EntityCountsDTO
from application.dtos.identity_dtos import SessionUserDTO
from domain.identity.entities import Role


@pytest.fixture(autouse=True)
def counts(dashboard_service):
    dashboard_service.get_entity_counts.return_value = EntityCountsDTO(
        families=0, members=0, users=0, cost_centers=0, categories=0,
    )


def _bar(html: str) -> str:
    match = re.search(r'<header class="auth-bar"[^>]*>.*?</header>', html, re.S)
    assert match is not None, "barra de status não encontrada"
    return match.group(0)


def _login_as(auth_service, role, name, username="quem", family_id=None):
    auth_service.find_session_user_by_username.return_value = SessionUserDTO(
        id=uuid.uuid4(), role=role, family_id=family_id, name=name, username=username, email="q@example.com", session_id="s",
    )


def test_the_bar_shows_who_is_logged_in_and_their_role(client):
    bar = _bar(client.get("/").get_data(as_text=True))

    assert "Conectado como" in bar
    assert "Administrador de Teste" in bar and "Administrador do sistema" in bar


@pytest.mark.parametrize("role, label", [
    (Role.SYSTEM_ADMIN, "Administrador do sistema"), (Role.FAMILY_ADMIN, "Administrador da família"),
    (Role.FAMILY_USER, "Usuário da família"),
])
def test_the_bar_shows_each_roles_label(client, auth_service, role, label):
    _login_as(auth_service, role, "Maria Souza", family_id=None if role is Role.SYSTEM_ADMIN else uuid.uuid4())

    bar = _bar(client.get("/").get_data(as_text=True))

    assert "Maria Souza" in bar and label in bar


def test_the_bar_shows_the_username_for_the_nameless_root(client, auth_service):
    _login_as(auth_service, Role.ROOT, None, username="root")

    bar = _bar(client.get("/").get_data(as_text=True))

    assert "<strong class=\"auth-bar-name\">root</strong>" in bar and "Root" in bar and "None" not in bar


def test_the_logout_button_is_a_post_form_with_csrf_inside_the_bar(client):
    bar = _bar(client.get("/").get_data(as_text=True))

    form = re.search(r'<form[^>]*class="auth-bar-logout"[^>]*>.*?</form>', bar, re.S).group(0)
    assert 'method="POST"' in form and 'action="/auth/logout"' in form
    assert 'name="csrf_token"' in form
    assert re.search(r'<button[^>]*type="submit"[^>]*>\s*Sair\s*</button>', form)


def test_there_is_exactly_one_logout_button_on_the_page(client):
    html = client.get("/").get_data(as_text=True)

    assert html.count('action="/auth/logout"') == 1


def test_the_bar_comes_first_in_the_page_before_the_sidebar_and_the_content(client):
    html = client.get("/").get_data(as_text=True)

    assert html.index('class="auth-bar"') < html.index('<aside class="sidebar"') < html.index('<main class="main-content"')
    assert html.index('<body class="app-body">') < html.index('class="auth-bar"')


def test_the_bar_order_is_user_then_account_menu_then_logout(client):
    bar = _bar(client.get("/").get_data(as_text=True))

    assert bar.index("Conectado como") < bar.index('class="account-menu"') < bar.index('class="auth-bar-logout"')


def test_change_password_is_not_a_visible_link_of_the_bar(client):
    """A troca de senha não fica solta na barra: só existe dentro do menu da conta."""
    bar = _bar(client.get("/").get_data(as_text=True))

    outside_menu = re.sub(r'<details class="account-menu">.*?</details>', "", bar, flags=re.S)
    assert "Alterar senha" not in outside_menu and "/auth/change-password" not in outside_menu


def test_change_password_lives_inside_the_account_settings_menu(client):
    bar = _bar(client.get("/").get_data(as_text=True))

    menu = re.search(r'<details class="account-menu">.*?</details>', bar, re.S).group(0)
    panel = re.search(r'<div class="account-menu-panel">.*?</div>', menu, re.S).group(0)
    assert "Configurações da conta" in panel
    assert re.search(r'<a href="/auth/change-password" class="account-menu-item">Alterar senha</a>', panel)


def test_the_account_menu_starts_collapsed_and_is_labelled(client):
    menu = re.search(r'<details class="account-menu"[^>]*>.*?</details>', _bar(client.get("/").get_data(as_text=True)), re.S).group(0)

    assert not re.match(r"<details[^>]*\sopen", menu)                      # recolhido por padrão
    assert re.search(r'<summary class="account-menu-trigger" aria-label="Configurações da conta"', menu)
    assert "Conta" in menu and "<svg" in menu                                # engrenagem + rótulo


def test_the_account_menu_script_is_loaded_for_logged_in_pages_only(client):
    html = client.get("/").get_data(as_text=True)
    assert 'js/account_menu.js' in html

    script = client.get("/static/js/account_menu.js").get_data(as_text=True)
    assert "Escape" in script and ".style" not in script


def test_the_account_menu_script_is_not_loaded_on_public_pages(client):
    assert "account_menu.js" not in client.get("/auth/login").get_data(as_text=True)


def test_the_logout_button_stays_visible_in_the_bar_not_inside_the_menu(client):
    bar = _bar(client.get("/").get_data(as_text=True))

    menu = re.search(r'<details class="account-menu">.*?</details>', bar, re.S).group(0)
    assert "/auth/logout" not in menu and "/auth/logout" in bar


def test_the_bar_content_is_right_aligned(client):
    css = client.get("/static/css/app.css").get_data(as_text=True)

    rule = re.search(r"\.auth-bar \{([^}]*)\}", css).group(1)
    assert "justify-content: flex-end" in rule
    assert "margin-left: auto" not in css.split("Barra de status da autenticação")[1].split(".account-menu {")[0]


def test_the_menu_panel_opens_downward_aligned_to_the_right_edge(client):
    css = client.get("/static/css/app.css").get_data(as_text=True)

    panel = re.search(r"\.account-menu-panel \{([^}]*)\}", css).group(1)
    assert "position: absolute" in panel and "right: 0" in panel and "top: calc(100% + " in panel


def test_the_old_sidebar_user_block_is_gone(client):
    html = client.get("/").get_data(as_text=True)

    assert "sidebar-user" not in html


def test_the_sidebar_and_the_content_share_one_shell_below_the_bar(client):
    html = client.get("/").get_data(as_text=True)

    shell = re.search(r'<div class="app-shell">(.*)</div>\s*(?:<!--.*?-->\s*)?<script>', html, re.S).group(1)
    assert '<aside class="sidebar"' in shell and '<main class="main-content"' in shell


@pytest.mark.parametrize("path", ["/", "/auth/change-password"])
def test_the_bar_is_on_every_page_that_uses_the_main_layout(client, path):
    assert 'class="auth-bar"' in client.get(path).get_data(as_text=True)


def test_the_bar_is_on_the_user_pages_too(client, family_service):
    family_service.list_families.return_value = []

    assert 'class="auth-bar"' in client.get("/user/new").get_data(as_text=True)


@pytest.mark.parametrize("path", ["/auth/login", "/auth/forgot-password", "/auth/activate/t", "/auth/recover/t"])
def test_the_bar_is_not_on_the_public_pages(client, credential_service, path):
    from application.dtos.identity_dtos import InvitationInfoDTO
    from domain.identity.invitations import InvitationPurpose

    credential_service.inspect_invitation.return_value = InvitationInfoDTO(purpose=InvitationPurpose.ACTIVATION, requires_code=True)
    html = client.get(path).get_data(as_text=True)

    assert "auth-bar" not in html and "Conectado como" not in html and "/auth/logout" not in html


def test_the_bar_escapes_the_name(client, auth_service):
    _login_as(auth_service, Role.SYSTEM_ADMIN, "<script>alert(1)</script>")

    html = client.get("/").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in _bar(html)


def test_the_bar_has_no_inline_style_or_handlers(client):
    bar = _bar(client.get("/").get_data(as_text=True))
    assert "style=" not in bar and not re.search(r"\son\w+=", bar)


def test_the_bar_is_labelled_for_screen_readers(client):
    assert 'aria-label="Sessão"' in _bar(client.get("/").get_data(as_text=True))


def test_the_css_defines_the_bar_and_keeps_it_visible(client):
    css = client.get("/static/css/app.css").get_data(as_text=True)

    rule = re.search(r"\.auth-bar \{([^}]*)\}", css).group(1)
    assert "position: sticky" in rule and "top: 0" in rule
    assert "body.app-body" in css and ".app-shell" in css
    assert ".sidebar-user" not in css


def test_the_dev_banner_and_the_bar_coexist(client):
    html = client.get("/").get_data(as_text=True)

    assert "DESLIGADA" in html and 'class="auth-bar"' in html
