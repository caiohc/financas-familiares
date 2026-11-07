"""Ordenação pelo cabeçalho das listagens (fatia Família e Usuários)."""
import re
import uuid
from decimal import Decimal
from html import unescape
from urllib.parse import parse_qs, urlparse

import pytest

from application.dtos.family_dtos import FamilyCostCenterResponseDTO, FamilyResponseDTO, MemberResponseDTO
from application.dtos.identity_dtos import UserResponseDTO
from domain.identity.entities import AccountStatus, Role
from fakes.pagination import page_of
from support import assert_listing_call

def _family(name: str = "Silva") -> FamilyResponseDTO:
    return FamilyResponseDTO(id=uuid.uuid4(), name=name, current_balance=Decimal("0.00"))

def _member(n: int = 1) -> MemberResponseDTO:
    return MemberResponseDTO(id=uuid.uuid4(), family_id=uuid.uuid4(), name=f"Membro {n}")

def _cost_center(n: int = 1) -> FamilyCostCenterResponseDTO:
    return FamilyCostCenterResponseDTO(id=uuid.uuid4(), family_id=uuid.uuid4(), name=f"Centro {n}", description=None)

def _user(n: int = 1) -> UserResponseDTO:
    return UserResponseDTO(
        id=uuid.uuid4(), role=Role.FAMILY_USER, family_id=uuid.uuid4(), name=f"Pessoa {n}",
        username=f"pessoa{n}", email=f"pessoa{n}@example.com", status=AccountStatus.ACTIVE, is_active=True, is_pending=False,
    )

# (url, serviço-double, método paginado, item, campos ordenáveis)
LISTINGS = [
    ("/family/list", "family_service", "list_families_page", lambda: _family("Família 1"), ["name"]),
    ("/member/list", "member_service", "list_all_members_page", _member, ["name", "family"]),
    (
        "/cost-center/list", "family_cost_center_service", "list_all_family_cost_centers_page",
        _cost_center, ["name", "family"],
    ),
    ("/user/list", "user_service", "list_users_page", _user, ["name", "username", "email"]),
]

@pytest.fixture(params=LISTINGS, ids=["family", "member", "cost_center", "user"])
def listing(request, client, family_service, member_service, family_cost_center_service, user_service):
    url, service_name, method, make_item, fields = request.param
    services = {
        "family_service": family_service,
        "member_service": member_service,
        "family_cost_center_service": family_cost_center_service,
        "user_service": user_service,
    }
    family_service.list_families.return_value = []
    paged_method = getattr(services[service_name], method)
    paged_method.return_value = page_of([])
    return url, paged_method, make_item, fields

def _header(html: str, field: str) -> str:
    """O <th> cujo link ordena por `field`."""
    for th in re.findall(r"<th[^>]*>.*?</th>", html, re.S):
        link = re.search(r'href="([^"]+)"', th)
        if link and parse_qs(urlparse(unescape(link.group(1))).query).get("sort") == [field]:
            return th
    raise AssertionError(f"cabeçalho ordenável por {field!r} não encontrado")

def _query(th: str) -> dict:
    return parse_qs(urlparse(unescape(re.search(r'href="([^"]+)"', th).group(1))).query)

def test_list_forwards_sort_and_dir_from_the_query_string(client, listing):
    url, paged_method, _, _ = listing

    client.get(f"{url}?sort=name&dir=desc&page=2&per_page=25")

    assert_listing_call(paged_method, page=2, page_size=25, sort_by="name", sort_dir="desc", search=None)

def test_list_without_sort_asks_the_service_for_its_defaults(client, listing):
    url, paged_method, _, _ = listing

    client.get(url)

    assert_listing_call(paged_method, page=None, page_size=None, sort_by=None, sort_dir=None, search=None)

def test_sortable_headers_exist_for_each_allowed_field(client, listing):
    url, paged_method, make_item, fields = listing
    paged_method.return_value = page_of([make_item()])

    html = client.get(url).get_data(as_text=True)

    for field in fields:
        _header(html, field)

def test_actions_column_is_not_sortable(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of([make_item()])

    html = client.get(url).get_data(as_text=True)

    actions = next(th for th in re.findall(r"<th[^>]*>.*?</th>", html, re.S) if "Ações" in th)
    assert "href" not in actions

def test_active_column_shows_arrow_and_aria_sort_and_the_others_do_not(client, listing):
    url, paged_method, make_item, fields = listing
    paged_method.return_value = page_of([make_item()], sort_by="name", sort_dir="asc")

    html = client.get(url).get_data(as_text=True)

    active = _header(html, "name")
    assert 'aria-sort="ascending"' in active
    assert "sort-arrow" in active
    for other in fields:
        if other != "name":
            th = _header(html, other)
            assert "aria-sort" not in th
            assert "sort-arrow" not in th

def test_arrow_points_down_when_descending(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of([make_item()], sort_by="name", sort_dir="desc", search=None)

    html = client.get(url).get_data(as_text=True)

    th = _header(html, "name")
    assert 'aria-sort="descending"' in th
    assert "sort-arrow-desc" in th and "sort-arrow-asc" not in th

def test_clicking_the_active_header_toggles_direction_and_returns_to_first_page(client, listing):
    url, paged_method, make_item, _ = listing
    paged_method.return_value = page_of([make_item()], page=3, page_size=25, total=80, sort_by="name", sort_dir="asc")

    ascending = _query(_header(client.get(url).get_data(as_text=True), "name"))
    paged_method.return_value = page_of([make_item()], page=3, page_size=25, total=80, sort_by="name", sort_dir="desc", search=None)
    descending = _query(_header(client.get(url).get_data(as_text=True), "name"))

    assert ascending["dir"] == ["desc"] and ascending["page"] == ["1"] and ascending["per_page"] == ["25"]
    assert descending["dir"] == ["asc"] and descending["page"] == ["1"]

def test_clicking_another_header_starts_ascending_and_returns_to_first_page(client, listing):
    url, paged_method, make_item, fields = listing
    other = next((f for f in fields if f != "name"), None)
    if other is None:
        pytest.skip("só há um campo ordenável nesta listagem")
    paged_method.return_value = page_of([make_item()], page=2, page_size=10, total=30, sort_by="name", sort_dir="desc", search=None)

    query = _query(_header(client.get(url).get_data(as_text=True), other))

    assert query["sort"] == [other]
    assert query["dir"] == ["asc"]
    assert query["page"] == ["1"]

def test_pagination_links_keep_the_current_sort(client, listing):
    url, paged_method, make_item, fields = listing
    paged_method.return_value = page_of([make_item()], page=2, page_size=10, total=45, sort_by=fields[-1], sort_dir="desc")

    html = unescape(client.get(url).get_data(as_text=True))

    pagination = re.search(r'<nav class="pagination".*?</nav>', html, re.S).group(0)
    links = [parse_qs(urlparse(h).query) for h in re.findall(r'href="([^"]+)"', pagination)]
    assert len(links) == 5  # 3 tamanhos + anterior + próxima
    assert all(q["sort"] == [fields[-1]] and q["dir"] == ["desc"] for q in links)
