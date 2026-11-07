"""Botão de mostrar/ocultar senha (olho aberto / olho riscado) em todas as telas que pedem uma senha."""
import re

import pytest

from application.dtos.identity_dtos import InvitationInfoDTO
from domain.identity.invitations import InvitationPurpose


@pytest.fixture(autouse=True)
def pages(credential_service):
    credential_service.inspect_invitation.return_value = InvitationInfoDTO(purpose=InvitationPurpose.ACTIVATION, requires_code=True)


# (caminho, {campo de senha: valor esperado de autocomplete}). "current-password" ajuda o gerenciador a preencher
# a senha que já existe; "new-password" faz o navegador oferecer uma senha nova e não preencher a antiga.
PAGES = {
    "login": ("/auth/login", {"password": "current-password"}),
    "activation": ("/auth/activate/t", {"password": "new-password", "password_confirmation": "new-password"}),
    "recovery": ("/auth/recover/t", {"password": "new-password", "password_confirmation": "new-password"}),
    "change": ("/auth/change-password", {
        "current_password": "current-password", "password": "new-password", "password_confirmation": "new-password",
    }),
}


def _field_block(html: str, field_id: str) -> str:
    match = re.search(rf'<div class="password-field">(?:(?!</div>).)*id="{field_id}"(?:(?!</div>).)*</div>', html, re.S)
    assert match is not None, f"campo de senha {field_id!r} dentro de .password-field não encontrado"
    return match.group(0)


@pytest.fixture(params=sorted(PAGES))
def page(request, client):
    path, fields = PAGES[request.param]
    response = client.get(path)
    assert response.status_code == 200, path
    return response.get_data(as_text=True), fields


def test_each_password_field_has_its_own_toggle_button(page):
    html, fields = page
    for field_id in fields:
        button = re.search(r"<button[^>]*>", _field_block(html, field_id)).group(0)
        assert 'type="button"' in button                       # nunca envia o formulário
        assert f'data-password-toggle="{field_id}"' in button
        assert 'aria-label="Mostrar senha"' in button and 'aria-pressed="false"' in button


def test_toggle_offers_both_the_open_and_the_crossed_out_eye(page):
    html, fields = page
    for field_id in fields:
        block = _field_block(html, field_id)
        assert block.count("<svg") == 2
        assert 'class="icon icon-eye"' in block and 'class="icon icon-eye-off"' in block
        assert 'aria-hidden="true"' in block


def test_password_fields_start_hidden_and_are_never_prefilled(page):
    html, fields = page
    for field_id in fields:
        block = _field_block(html, field_id)
        assert re.search(r'<input[^>]*type="password"', block)
        assert 'value="' not in re.search(r"<input[^>]*>", block).group(0)


def test_password_fields_allow_pasting(page):
    html, _ = page
    assert "onpaste" not in html.lower() and "paste" not in html.lower()


def test_each_password_field_declares_the_right_autocomplete(page):
    html, fields = page
    for field_id, expected in fields.items():
        assert re.search(r'autocomplete="([^"]+)"', _field_block(html, field_id)).group(1) == expected, field_id


def test_the_page_loads_the_toggle_script(page, client):
    html, _ = page
    src = re.search(r'<script src="([^"]+password_toggle\.js)"', html).group(1)

    response = client.get(src)

    assert response.status_code == 200
    script = response.get_data(as_text=True)
    assert "data-password-toggle" in script and "aria-pressed" in script
    assert ".style" not in script               # a aparência vem do CSS, não do JavaScript


def test_markup_has_no_inline_style_or_inline_handlers(page):
    html, _ = page
    assert "style=" not in html
    assert not re.search(r'\son\w+="', html)
    inline = [s for s in re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", html, re.S) if s.strip()]
    assert all("sidebarCollapsed" in s or "sidebarToggle" in s for s in inline)     # só o do menu lateral (layout)


def test_css_swaps_the_eye_by_aria_pressed(client):
    css = client.get("/static/css/app.css").get_data(as_text=True)

    assert ".password-toggle .icon-eye-off" in css
    assert '.password-toggle[aria-pressed="true"] .icon-eye' in css
    assert '.password-toggle[aria-pressed="true"] .icon-eye-off' in css


def test_other_pages_do_not_load_the_toggle_script(client, user_service):
    from fakes.pagination import page_of

    user_service.list_users_page.return_value = page_of([])

    assert "password_toggle.js" not in client.get("/user/list").get_data(as_text=True)


def test_the_user_form_has_no_password_fields_anymore(client, family_service):
    family_service.list_families.return_value = []

    html = client.get("/user/new").get_data(as_text=True)

    assert "password-toggle" not in html and "password_toggle.js" not in html
