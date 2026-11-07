"""Paginação das listagens (famílias, membros, centros de custo e usuários)."""
import re
import uuid
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest

from application.dtos.family_dtos import FamilyCostCenterResponseDTO, FamilyResponseDTO, MemberResponseDTO
from application.dtos.identity_dtos import UserResponseDTO
from domain.identity.entities import AccountStatus, Role
from fakes.pagination import page_of
from support import assert_listing_call

def _family(name: str = "Silva") -> FamilyResponseDTO:
    return FamilyResponseDTO(id=uuid.uuid4(), name=name, current_balance=Decimal("0.00"))

# (url da listagem, nome do serviço-double, método paginado, fábrica de item)
LISTINGS = [
    ("/family/list", "family_service", "list_families_page", lambda n: _family(f"Família {n}")),
    (
        "/member/list", "member_service", "list_all_members_page",
        lambda n: MemberResponseDTO(id=uuid.uuid4(), family_id=uuid.uuid4(), name=f"Membro {n}"),
    ),
    (
        "/cost-center/list", "family_cost_center_service", "list_all_family_cost_centers_page",
        lambda n: FamilyCostCenterResponseDTO(
            id=uuid.uuid4(), family_id=uuid.uuid4(), name=f"Centro {n}", description=None
        ),
    ),
    (
        "/user/list", "user_service", "list_users_page",
        lambda n: UserResponseDTO(
            id=uuid.uuid4(), role=Role.FAMILY_USER, family_id=uuid.uuid4(), name=f"Pessoa {n}",
            username=f"pessoa{n}", email=f"pessoa{n}@example.com", status=AccountStatus.ACTIVE, is_active=True, is_pending=False,
        ),
    ),
]
LISTING_IDS = ["family", "member", "cost_center", "user"]

@pytest.fixture(params=LISTINGS, ids=LISTING_IDS)
def listing(request, client, family_service, member_service, family_cost_center_service, user_service):
    url, service_name, method, make_item = request.param
    services = {
        "family_service": family_service,
        "member_service": member_service,
        "family_cost_center_service": family_cost_center_service,
        "user_service": user_service,
    }
    family_service.list_families.return_value = []
    paged_method = getattr(services[service_name], method)
    paged_method.return_value = page_of([])
    return url, paged_method, make_item

def _hrefs(html: str, base_url: str) -> list[tuple[str, dict]]:
    found = []
    for href in re.findall(r'href="([^"]+)"', html):
        parsed = urlparse(href.replace("&amp;", "&"))
        if parsed.path == base_url:
            found.append((parsed.path, parse_qs(parsed.query)))
    return found

def test_list_without_query_asks_the_service_for_its_defaults(client, listing):
    url, paged_method, _ = listing

    client.get(url)

    assert_listing_call(paged_method, page=None, page_size=None, sort_by=None, sort_dir=None, search=None)

def test_list_forwards_page_and_per_page_from_the_query_string(client, listing):
    url, paged_method, _ = listing

    client.get(f"{url}?page=3&per_page=25")

    assert_listing_call(paged_method, page=3, page_size=25, sort_by=None, sort_dir=None, search=None)

@pytest.mark.parametrize("query", ["page=abc&per_page=xyz", "page=&per_page=", "page=1.5"])
def test_list_ignores_non_numeric_query_values(client, listing, query):
    url, paged_method, _ = listing

    response = client.get(f"{url}?{query}")

    assert response.status_code == 200
    assert_listing_call(paged_method, page=None, page_size=None, sort_by=None, sort_dir=None, search=None)

def test_list_shows_where_the_user_is(client, listing):
    url, paged_method, make_item = listing
    paged_method.return_value = page_of([make_item(n) for n in range(1, 11)], page=2, page_size=10, total=25)

    html = client.get(url).get_data(as_text=True)

    assert "Página 2 de 3" in html
    assert "25 registros" in html

def test_list_offers_the_three_page_sizes_and_marks_the_current_one(client, listing):
    url, paged_method, make_item = listing
    paged_method.return_value = page_of([make_item(1)], page=1, page_size=25, total=1)

    html = client.get(url).get_data(as_text=True)

    sizes = {int(query["per_page"][0]): query for _, query in _hrefs(html, url) if "per_page" in query}
    assert set(sizes) == {10, 25, 50}
    # Trocar o tamanho volta para a primeira página
    assert all(query["page"] == ["1"] for query in sizes.values())
    current = re.search(r'<[^>]*aria-current="true"[^>]*>\s*([^<]+)<', html)
    assert current is not None and current.group(1).strip() == "25"

def test_list_navigation_links_keep_the_chosen_page_size(client, listing):
    url, paged_method, make_item = listing
    paged_method.return_value = page_of([make_item(1)], page=2, page_size=25, total=60)

    html = client.get(url).get_data(as_text=True)

    links = {(q["page"][0], q["per_page"][0]) for _, q in _hrefs(html, url) if "page" in q and "per_page" in q}
    assert ("1", "25") in links  # anterior
    assert ("3", "25") in links  # próxima

def test_first_page_has_no_previous_link_and_last_page_has_no_next_link(client, listing):
    url, paged_method, make_item = listing

    paged_method.return_value = page_of([make_item(1)], page=1, page_size=10, total=15)
    first = client.get(url).get_data(as_text=True)
    paged_method.return_value = page_of([make_item(1)], page=2, page_size=10, total=15)
    last = client.get(url).get_data(as_text=True)

    assert "Anterior" in first and 'href' not in re.search(r'<[^>]*>\s*Anterior', first).group(0)
    assert "Próxima" in last and 'href' not in re.search(r'<[^>]*>\s*Próxima', last).group(0)
    assert re.search(r'<a [^>]*href[^>]*>\s*Próxima', first)
    assert re.search(r'<a [^>]*href[^>]*>\s*Anterior', last)

def test_list_with_a_single_page_still_shows_the_page_size_choice(client, listing):
    url, paged_method, make_item = listing
    paged_method.return_value = page_of([make_item(1)], page=1, page_size=10, total=1)

    html = client.get(url).get_data(as_text=True)

    assert "Página 1 de 1" in html
    assert {10, 25, 50} <= {int(q["per_page"][0]) for _, q in _hrefs(html, url) if "per_page" in q}
