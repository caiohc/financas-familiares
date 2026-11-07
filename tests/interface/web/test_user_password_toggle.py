"""Botão de mostrar/ocultar senha (olho aberto / olho riscado) no cadastro de usuário."""
import re
import uuid

import pytest

from application.dtos.identity_dtos import UserResponseDTO
from domain.identity.entities import Role

PASSWORD_FIELDS = ["temporary_password", "temporary_password_confirmation"]


@pytest.fixture
def new_form_html(client, family_service) -> str:
    family_service.list_families.return_value = []
    return client.get("/user/new").get_data(as_text=True)


def _field_block(html: str, field_id: str) -> str:
    match = re.search(rf'<div class="password-field">(?:(?!</div>).)*id="{field_id}"(?:(?!</div>).)*</div>', html, re.S)
    assert match is not None, f"campo de senha {field_id!r} dentro de .password-field não encontrado"
    return match.group(0)


@pytest.mark.parametrize("field_id", PASSWORD_FIELDS)
def test_each_password_field_has_its_own_toggle_button(new_form_html, field_id):
    block = _field_block(new_form_html, field_id)

    button = re.search(r"<button[^>]*>", block).group(0)
    assert 'type="button"' in button            # nunca envia o formulário
    assert f'data-password-toggle="{field_id}"' in button
    assert 'aria-label="Mostrar senha"' in button
    assert 'aria-pressed="false"' in button


@pytest.mark.parametrize("field_id", PASSWORD_FIELDS)
def test_toggle_offers_both_the_open_and_the_crossed_out_eye(new_form_html, field_id):
    block = _field_block(new_form_html, field_id)

    assert block.count("<svg") == 2
    assert 'class="icon icon-eye"' in block and 'class="icon icon-eye-off"' in block
    assert 'aria-hidden="true"' in block        # o rótulo acessível está no botão, não no desenho


@pytest.mark.parametrize("field_id", PASSWORD_FIELDS)
def test_password_fields_still_start_hidden(new_form_html, field_id):
    block = _field_block(new_form_html, field_id)

    assert re.search(r'<input[^>]*type="password"', block)


def test_the_page_loads_the_toggle_script(new_form_html, client):
    src = re.search(r'<script src="([^"]+password_toggle\.js)"', new_form_html).group(1)

    response = client.get(src)

    assert response.status_code == 200
    script = response.get_data(as_text=True)
    assert "data-password-toggle" in script or "[data-password-toggle]" in script
    assert "aria-pressed" in script
    assert ".style" not in script               # a aparência vem do CSS, não do JavaScript


def test_markup_has_no_inline_style_or_inline_script(new_form_html):
    assert "style=" not in new_form_html
    inline_scripts = [s for s in re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", new_form_html, re.S) if s.strip()]
    # só o script do menu lateral (herdado do layout) é inline
    assert all("sidebarCollapsed" in s or "sidebarToggle" in s for s in inline_scripts)


def test_css_swaps_the_eye_by_aria_pressed(client):
    css = client.get("/static/css/app.css").get_data(as_text=True)

    assert ".password-toggle .icon-eye-off" in css
    assert '.password-toggle[aria-pressed="true"] .icon-eye' in css
    assert '.password-toggle[aria-pressed="true"] .icon-eye-off' in css


def test_edit_form_has_no_password_fields_toggle_or_script(client, user_service, family_service):
    family_service.list_families.return_value = []
    user = UserResponseDTO(
        id=uuid.uuid4(), role=Role.SYSTEM_ADMIN, family_id=None, name="Caio", username="caio",
        email="caio@example.com", must_change_password=True,
    )
    user_service.get_user.return_value = user

    html = client.get(f"/user/edit/{user.id}").get_data(as_text=True)

    assert "password-toggle" not in html
    assert "password_toggle.js" not in html
    assert 'type="password"' not in html


def test_other_pages_do_not_load_the_toggle_script(client, user_service):
    from fakes.pagination import page_of

    user_service.list_users_page.return_value = page_of([])

    assert "password_toggle.js" not in client.get("/user/list").get_data(as_text=True)
