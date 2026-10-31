"""Pesquisa nas listagens (fatia Família e Usuários): caixa única, enviada com Enter ou com o ícone de busca."""
import re
import uuid
from decimal import Decimal
from html import unescape
from urllib.parse import parse_qs, urlparse

import pytest

from application.dtos.family_dtos import FamilyCostCenterResponseDTO, FamilyResponseDTO, MemberResponseDTO
from application.dtos.identity_dtos import UserResponseDTO
from domain.identity.entities import Role
from fakes.pagination import page_of

def _family(name: str = "Família Silva") -> FamilyResponseDTO:
    return FamilyResponseDTO(id=uuid.uuid4(), name=name, current_balance=Decimal("0.00"))

def _member(name: str = "Ana") -> MemberResponseDTO:
    return MemberResponseDTO(id=uuid.uuid4(), family_id=uuid.uuid4(), name=name)

def _cost_center(name: str = "Escola") -> FamilyCostCenterResponseDTO:
    return FamilyCostCenterResponseDTO(id=uuid.uuid4(), family_id=uuid.uuid4(), name=name, description=None)

def _user(name: str = "Ana") -> UserResponseDTO:
    return UserResponseDTO(
        id=uuid.uuid4(), role=Role.FAMILY_USER, family_id=uuid.uuid4(), name=name, username="ana",
        email="ana@example.com", must_change_password=True,
    )

LISTINGS = [
    ("/family/list", "family_service", "list_families_page", _family, "nome"),
    ("/member/list", "member_service", "list_all_members_page", _member, "nome ou família"),
    (
        "/cost-center/list", "family_cost_center_service", "list_all_family_cost_centers_page",
        _cost_center, "nome ou família",
    ),
    ("/user/list", "user_service", "list_users_page", _user, "nome, usuário ou e-mail"),
]

@pytest.fixture(params=LISTINGS, ids=["family", "member", "cost_center", "user"])
def listing(request, client, family_service, member_service, family_cost_center_service, user_service):
    url, service_name, method, make_item, scope = request.param
    services = {
        "family_service": family_service,
        "member_service": member_service,
        "family_cost_center_service": family_cost_center_service,
        "user_service": user_service,
    }
    family_service.list_families.return_value = []
    paged_method = getattr(services[service_name], method)
    paged_method.return_value = page_of([])
    return url, paged_method, make_item, scope

def _form(html: str) -> str:
    match = re.search(r'<form[^>]*class="search-form"[^>]*>.*?</form>', html, re.S)
    assert match is not None, "formulário de pesquisa não encontrado"
    return match.group(0)

def _clear_link(html: str):
    return re.search(r'<a [^>]*class="[^"]*search-clear[^"]*"[^>]*>', html)

def _href(tag: str) -> dict:
    return parse_qs(urlparse(unescape(re.search(r'href="([^"]+)"', tag).group(1))).query)

def test_list_forwards_q_to_the_service(client, listing):
    url, paged_method, _, _ = listing

    client.get(f"{url}?q=silva&page=2&per_page=25&sort=name&dir=desc")

    paged_method.assert_called_once_with(
        page=2, page_size=25, sort_by="name", sort_dir="desc", search="silva"
    )

def test_search_form_is_a_get_form_submitted_by_enter_or_by_the_search_icon(client, listing):
    url, _, _, _ = listing

    form = _form(client.get(url).get_data(as_text=True))

    assert 'method="get"' in form.lower()
    assert f'action="{url}"' in form
    assert re.search(r'<input[^>]*type="search"[^>]*name="q"|<input[^>]*name="q"[^>]*type="search"', form)
    button = re.search(r'<button[^>]*type="submit"[^>]*>', form)
    assert button is not None and 'aria-label="Pesquisar"' in button.group(0)
    assert "<svg" in form

def test_search_form_placeholder_says_where_the_search_looks(client, listing):
    url, _, _, scope = listing

    form = _form(client.get(url).get_data(as_text=True))

    assert f'placeholder="Pesquisar por {scope}"' in form

def test_search_form_carries_page_size_and_sort_but_not_the_page(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of(
        [make_item()], page=3, page_size=25, total=80, sort_by="name", sort_dir="desc"
    )

    form = _form(client.get(url).get_data(as_text=True))

    hidden = dict(re.findall(r'<input[^>]*type="hidden"[^>]*name="(\w+)"[^>]*value="([^"]*)"', form))
    assert hidden == {"per_page": "25", "sort": "name", "dir": "desc"}

def test_search_input_keeps_the_term_after_submitting(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of([make_item()], search="silva")

    form = _form(client.get(f"{url}?q=silva").get_data(as_text=True))

    assert 'value="silva"' in form

def test_search_term_is_escaped_in_the_input(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of([make_item()], search='"><script>x</script>')

    html = client.get(url).get_data(as_text=True)

    assert "<script>x</script>" not in html

def test_clear_link_only_shows_while_a_search_is_active(client, listing):
    url, paged_method, make_item, _ = listing

    paged_method.return_value = page_of([make_item()])
    without = client.get(url).get_data(as_text=True)
    paged_method.return_value = page_of([make_item()], search="silva")
    with_search = client.get(url).get_data(as_text=True)

    assert _clear_link(without) is None
    assert _clear_link(with_search) is not None

def test_clear_link_drops_the_term_and_keeps_size_and_sort(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of(
        [make_item()], page=2, page_size=50, total=80, sort_by="name", sort_dir="desc", search="silva"
    )

    link = _clear_link(client.get(url).get_data(as_text=True)).group(0)

    query = _href(link)
    assert "q" not in query
    assert query["page"] == ["1"]
    assert query["per_page"] == ["50"] and query["sort"] == ["name"] and query["dir"] == ["desc"]

def test_result_summary_shows_the_count_and_the_term(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of([make_item()] * 3, total=12, search="silva")

    html = unescape(client.get(url).get_data(as_text=True))

    assert '12 resultados para "silva"' in html

def test_result_summary_uses_the_singular_for_one_result(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of([make_item()], search="silva")

    html = unescape(client.get(url).get_data(as_text=True))

    assert '1 resultado para "silva"' in html

def test_no_summary_without_a_search(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of([make_item()])

    assert " para &#34;" not in client.get(url).get_data(as_text=True)

def test_empty_search_says_there_are_no_results_instead_of_an_empty_registry(client, listing):
    url, paged_method, _, _ = listing
    paged_method.return_value = page_of([], search="xyz")

    html = unescape(client.get(url).get_data(as_text=True))

    assert 'Nenhum resultado para "xyz".' in html
    assert "cadastrad" not in html.split('class="empty-state"')[1].split("</td>")[0]

def test_pagination_runs_over_the_results_and_keeps_the_term_in_every_link(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of(
        [make_item()], page=2, page_size=10, total=25, sort_by="name", sort_dir="asc", search="silva"
    )

    html = unescape(client.get(url).get_data(as_text=True))

    assert "Página 2 de 3" in html
    pagination = re.search(r'<nav class="pagination".*?</nav>', html, re.S).group(0)
    links = [parse_qs(urlparse(h).query) for h in re.findall(r'href="([^"]+)"', pagination)]
    assert len(links) == 5
    assert all(q["q"] == ["silva"] for q in links)

def test_sortable_headers_keep_the_term_and_return_to_the_first_page(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of([make_item()], page=2, total=25, search="silva")

    html = unescape(client.get(url).get_data(as_text=True))

    header = next(th for th in re.findall(r"<th[^>]*>.*?</th>", html, re.S) if "sort=name" in th)
    query = _href(header)
    assert query["q"] == ["silva"] and query["page"] == ["1"]

def test_matched_part_of_the_name_is_highlighted_ignoring_case_and_accents(client, family_service):
    family_service.list_families_page.return_value = page_of(
        [_family("Família Silva"), _family("Álvares")], search="SIL"
    )
    html = client.get("/family/list?q=SIL").get_data(as_text=True)
    assert "Família <mark>Sil</mark>va" in html

    family_service.list_families_page.return_value = page_of([_family("Álvares")], search="alv")
    html = client.get("/family/list?q=alv").get_data(as_text=True)
    assert "<mark>Álv</mark>ares" in html

def test_highlight_does_not_let_the_data_inject_html(client, family_service):
    family_service.list_families_page.return_value = page_of([_family("<b>Silva</b>")], search="silva")

    html = client.get("/family/list?q=silva").get_data(as_text=True)

    assert "<b>Silva</b>" not in html
    assert "&lt;b&gt;<mark>Silva</mark>&lt;/b&gt;" in html

def test_family_column_is_highlighted_in_the_member_list(client, member_service, family_service):
    family = _family("Família Silva")
    family_service.list_families.return_value = [family]
    member = MemberResponseDTO(id=uuid.uuid4(), family_id=family.id, name="Ana")
    member_service.list_all_members_page.return_value = page_of([member], search="silva")

    html = client.get("/member/list?q=silva").get_data(as_text=True)

    assert "Família <mark>Silva</mark>" in html
