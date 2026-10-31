"""Comportamentos de interface compartilhados pelas listagens e pela barra lateral."""
import re
import pytest
import uuid
from decimal import Decimal

from application.dtos.family_dtos import FamilyCostCenterResponseDTO, FamilyResponseDTO, MemberResponseDTO
from fakes.pagination import page_of

def _family(name: str) -> FamilyResponseDTO:
    return FamilyResponseDTO(id=uuid.uuid4(), name=name, current_balance=Decimal("0.00"))

def _sidebar_link(html: str, href: str) -> str:
    match = re.search(rf'<a href="{re.escape(href)}"[^>]*>', html)
    assert match is not None, f"link {href} não encontrado na barra lateral"
    return match.group(0)

def test_sidebar_highlights_only_the_current_section(client, member_service):
    member_service.list_all_members_page.return_value = page_of([])

    html = client.get("/member/list").get_data(as_text=True)

    assert 'class="active"' in _sidebar_link(html, "/member/list")
    assert "active" not in _sidebar_link(html, "/family/list")

def test_sidebar_marks_unbuilt_sections_as_coming_soon_instead_of_dead_links(client, family_service):
    family_service.list_families.return_value = []

    html = client.get("/family/list").get_data(as_text=True)

    assert 'href="#"' not in html
    for label in ("Contas bancárias", "Cartões de crédito", "Auditoria de transações"):
        assert label in html
    assert html.count("em breve") == 3

def test_list_actions_use_svg_icons_instead_of_emoji(client, family_service):
    family_service.list_families_page.return_value = page_of([_family("Silva")])

    html = client.get("/family/list").get_data(as_text=True)
    actions = re.search(r'<div class="row-actions">(.*?)</div>', html, re.S).group(1)

    assert "✏️" not in html and "🗑️" not in html
    assert actions.count("<svg") == 2

def test_family_list_has_no_row_number_column(client, family_service):
    family_service.list_families_page.return_value = page_of([_family("Silva")])

    html = client.get("/family/list").get_data(as_text=True)

    assert "<th>#</th>" not in html

def test_member_list_keeps_the_order_given_by_the_service(client, member_service, family_service):
    souza, almeida = _family("Souza"), _family("Almeida")
    family_service.list_families.return_value = [souza, almeida]
    member_service.list_all_members_page.return_value = page_of([
        MemberResponseDTO(id=uuid.uuid4(), family_id=souza.id, name="Zélia"),
        MemberResponseDTO(id=uuid.uuid4(), family_id=almeida.id, name="Ana"),
        MemberResponseDTO(id=uuid.uuid4(), family_id=almeida.id, name="Bruno"),
    ])

    html = client.get("/member/list").get_data(as_text=True)

    positions = [html.index(name) for name in ("Zélia", "Ana", "Bruno")]
    assert positions == sorted(positions)

def test_cost_center_list_keeps_the_order_given_by_the_service(client, family_cost_center_service, family_service):
    souza, almeida = _family("Souza"), _family("Almeida")
    family_service.list_families.return_value = [souza, almeida]
    family_cost_center_service.list_all_family_cost_centers_page.return_value = page_of([
        FamilyCostCenterResponseDTO(id=uuid.uuid4(), family_id=souza.id, name="Escola", description=None),
        FamilyCostCenterResponseDTO(id=uuid.uuid4(), family_id=almeida.id, name="Filhos", description=None),
        FamilyCostCenterResponseDTO(id=uuid.uuid4(), family_id=almeida.id, name="Praia", description=None),
    ])

    html = client.get("/cost-center/list").get_data(as_text=True)

    positions = [html.index(name) for name in ("Escola", "Filhos", "Praia")]
    assert positions == sorted(positions)

def test_dropdown_options_use_the_app_dark_background(client):
    css = client.get("/static/css/app.css").get_data(as_text=True)

    # O popup do <select> é desenhado pelo navegador: sem estas regras ele fica branco
    assert "color-scheme: dark" in css
    rule = re.search(r"select\.form-control option\s*\{([^}]*)\}", css)
    assert rule is not None
    assert "background-color: var(--bg-color)" in rule.group(1)
    assert "color: var(--text-primary)" in rule.group(1)

def _toolbar(html: str) -> str:
    match = re.search(r'<div class="toolbar">(.*?)</form>\s*<div class="toolbar-actions">(.*?)</div>\s*</div>', html, re.S)
    assert match is not None, "barra com a pesquisa à esquerda e as ações à direita não encontrada"
    return match.group(0)

LISTINGS_WITH_NEW_BUTTON = [
    ("/family/list", "/family/new", "family_service", "list_families_page"),
    ("/member/list", "/member/new", "member_service", "list_all_members_page"),
    ("/cost-center/list", "/cost-center/new", "family_cost_center_service", "list_all_family_cost_centers_page"),
]



@pytest.mark.parametrize("url,new_url,service_name,method", LISTINGS_WITH_NEW_BUTTON, ids=["family", "member", "cost_center"])
def test_new_button_sits_on_the_right_of_the_search_bar_not_in_the_page_header(
    request, client, family_service, url, new_url, service_name, method
):
    getattr(request.getfixturevalue(service_name), method).return_value = page_of([])
    family_service.list_families.return_value = []

    html = client.get(url).get_data(as_text=True)

    toolbar = _toolbar(html)
    actions = toolbar.split('<div class="toolbar-actions">')[1]
    assert f'href="{new_url}"' in actions and "btn-success" in actions
    # A pesquisa vem primeiro (à esquerda) e as ações depois (à direita)
    assert toolbar.index('class="search-form"') < toolbar.index('class="toolbar-actions"')
    header = re.search(r'<div class="page-header">(.*?)</div>', html, re.S).group(1)
    assert "btn" not in header and "<h1>" in header
