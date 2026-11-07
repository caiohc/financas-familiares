import re

from application.dtos.dashboard_dtos import EntityCountsDTO

def _counts(families=2, members=3, users=5, cost_centers=1, categories=16) -> EntityCountsDTO:
    return EntityCountsDTO(
        families=families, members=members, users=users, cost_centers=cost_centers, categories=categories
    )

def _row(html: str, href: str) -> str:
    """Trecho da linha da tabela que contém o link informado."""
    match = re.search(rf'<tr>(?:(?!</tr>).)*href="{re.escape(href)}"(?:(?!</tr>).)*</tr>', html, re.S)
    assert match is not None, f"nenhuma linha com link para {href}"
    return match.group(0)

def test_dashboard_is_the_application_index(client, dashboard_service):
    dashboard_service.get_entity_counts.return_value = _counts()

    response = client.get("/")

    assert response.status_code == 200
    dashboard_service.get_entity_counts.assert_called_once_with()

def test_each_label_links_to_its_listing_and_shows_its_count(client, dashboard_service):
    dashboard_service.get_entity_counts.return_value = _counts(families=2, members=3, users=5, cost_centers=1, categories=16)

    html = client.get("/").get_data(as_text=True)

    expected = {
        "/family/list": ("Famílias", "2"),
        "/member/list": ("Membros", "3"),
        "/user/list": ("Usuários", "5"),
        "/cost-center/list": ("Centros de custo", "1"),
        "/category/list": ("Categorias", "16"),
    }
    for href, (label, count) in expected.items():
        row = _row(html, href)
        assert label in row
        assert f">{count}<" in row

def test_sidebar_dashboard_item_points_to_the_index(client, dashboard_service):
    dashboard_service.get_entity_counts.return_value = _counts()

    html = client.get("/").get_data(as_text=True)

    sidebar_link = re.search(r'<a href="([^"]*)"[^>]*>\s*<svg[^>]*>(?:(?!</a>).)*Dashboard</span>', html, re.S)
    assert sidebar_link is not None
    assert sidebar_link.group(1) == "/"
