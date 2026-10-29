"""Comportamentos de interface compartilhados pelas listagens e pela barra lateral."""
import re
import uuid
from decimal import Decimal

from application.dtos.family_dtos import FamilyCostCenterResponseDTO, FamilyResponseDTO, MemberResponseDTO

def _family(name: str) -> FamilyResponseDTO:
    return FamilyResponseDTO(id=uuid.uuid4(), name=name, current_balance=Decimal("0.00"))

def _sidebar_link(html: str, href: str) -> str:
    match = re.search(rf'<a href="{re.escape(href)}"[^>]*>', html)
    assert match is not None, f"link {href} não encontrado na barra lateral"
    return match.group(0)

def test_sidebar_highlights_only_the_current_section(client, member_service):
    member_service.list_all_members.return_value = []

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
    family_service.list_families.return_value = [_family("Silva")]

    html = client.get("/family/list").get_data(as_text=True)
    actions = re.search(r'<div class="row-actions">(.*?)</div>', html, re.S).group(1)

    assert "✏️" not in html and "🗑️" not in html
    assert actions.count("<svg") == 2

def test_family_list_has_no_row_number_column(client, family_service):
    family_service.list_families.return_value = [_family("Silva")]

    html = client.get("/family/list").get_data(as_text=True)

    assert "<th>#</th>" not in html

def test_member_list_is_ordered_by_family_then_name(client, member_service, family_service):
    souza, almeida = _family("Souza"), _family("Almeida")
    family_service.list_families.return_value = [souza, almeida]
    member_service.list_all_members.return_value = [
        MemberResponseDTO(id=uuid.uuid4(), family_id=souza.id, name="Ana"),
        MemberResponseDTO(id=uuid.uuid4(), family_id=almeida.id, name="Zélia"),
        MemberResponseDTO(id=uuid.uuid4(), family_id=almeida.id, name="Bruno"),
    ]

    html = client.get("/member/list").get_data(as_text=True)

    positions = [html.index(name) for name in ("Bruno", "Zélia", "Ana")]
    assert positions == sorted(positions)

def test_cost_center_list_is_ordered_by_family_then_name(client, family_cost_center_service, family_service):
    souza, almeida = _family("Souza"), _family("Almeida")
    family_service.list_families.return_value = [souza, almeida]
    family_cost_center_service.list_all_family_cost_centers.return_value = [
        FamilyCostCenterResponseDTO(id=uuid.uuid4(), family_id=souza.id, name="Escola", description=None),
        FamilyCostCenterResponseDTO(id=uuid.uuid4(), family_id=almeida.id, name="Praia", description=None),
        FamilyCostCenterResponseDTO(id=uuid.uuid4(), family_id=almeida.id, name="Filhos", description=None),
    ]

    html = client.get("/cost-center/list").get_data(as_text=True)

    positions = [html.index(name) for name in ("Filhos", "Praia", "Escola")]
    assert positions == sorted(positions)
