"""Regras de paginação compartilhadas pelos serviços de listagem (Família, Membro e Centro de Custo)."""
import pytest

from application.dtos.shared_dtos import ALLOWED_PAGE_SIZES, DEFAULT_PAGE_SIZE
from application.services.family_service import FamilyService
from application.services.family_cost_center_service import FamilyCostCenterService
from application.services.member_service import MemberService
from domain.family.entities import Family, FamilyCostCenter, Member
from fakes.family_fakes import FakeUnitOfWork

@pytest.fixture
def uow():
    return FakeUnitOfWork()

@pytest.fixture
def family_service(uow):
    return FamilyService(uow)

def _seed_families(uow: FakeUnitOfWork, count: int) -> None:
    for number in range(1, count + 1):
        uow.families.save(Family(name=f"Família {number:02d}"))

def test_allowed_page_sizes_and_default():
    assert ALLOWED_PAGE_SIZES == (10, 25, 50)
    assert DEFAULT_PAGE_SIZE == 10

def test_list_page_defaults_to_first_page_with_ten_records(family_service, uow):
    _seed_families(uow, 25)

    result = family_service.list_families_page()

    assert (result.page, result.page_size, result.total) == (1, 10, 25)
    assert [f.name for f in result.items] == [f"Família {n:02d}" for n in range(1, 11)]

def test_list_page_reports_total_pages_and_navigation_flags(family_service, uow):
    _seed_families(uow, 25)

    first = family_service.list_families_page(page=1)
    middle = family_service.list_families_page(page=2)
    last = family_service.list_families_page(page=3)

    assert first.total_pages == middle.total_pages == last.total_pages == 3
    assert (first.has_previous, first.has_next) == (False, True)
    assert (middle.has_previous, middle.has_next) == (True, True)
    assert (last.has_previous, last.has_next) == (True, False)
    assert len(last.items) == 5

@pytest.mark.parametrize("page_size", ALLOWED_PAGE_SIZES)
def test_list_page_accepts_each_allowed_page_size(family_service, uow, page_size):
    _seed_families(uow, 60)

    result = family_service.list_families_page(page_size=page_size)

    assert result.page_size == page_size
    assert len(result.items) == page_size

@pytest.mark.parametrize("page_size", [0, -5, 7, 11, 100, None])
def test_list_page_falls_back_to_default_for_a_page_size_outside_the_list(family_service, uow, page_size):
    _seed_families(uow, 30)

    result = family_service.list_families_page(page_size=page_size)

    assert result.page_size == DEFAULT_PAGE_SIZE
    assert len(result.items) == DEFAULT_PAGE_SIZE

@pytest.mark.parametrize("page", [0, -3, None])
def test_list_page_falls_back_to_first_page_for_an_invalid_page(family_service, uow, page):
    _seed_families(uow, 30)

    result = family_service.list_families_page(page=page)

    assert result.page == 1
    assert result.items[0].name == "Família 01"

def test_list_page_beyond_the_last_page_returns_the_last_page(family_service, uow):
    _seed_families(uow, 25)

    result = family_service.list_families_page(page=99)

    assert result.page == 3
    assert len(result.items) == 5

def test_list_page_when_empty_has_one_empty_page(family_service):
    result = family_service.list_families_page(page=4)

    assert (result.page, result.total, result.total_pages) == (1, 0, 1)
    assert result.items == []
    assert (result.has_previous, result.has_next) == (False, False)

def test_list_page_keeps_ordering_by_name_ignoring_case(family_service, uow):
    for name in ("família b", "Família C", "Família A"):
        uow.families.save(Family(name=name))

    result = family_service.list_families_page()

    assert [f.name for f in result.items] == ["Família A", "família b", "Família C"]

def test_member_service_paginates_across_families(uow):
    service = MemberService(uow)
    family_a, family_b = Family(name="A"), Family(name="B")
    for number in range(1, 13):
        owner = family_a if number % 2 else family_b
        uow.members.save(Member(family_id=owner.id, name=f"Membro {number:02d}"))

    first = service.list_all_members_page()
    second = service.list_all_members_page(page=2)

    assert (first.total, first.total_pages) == (12, 2)
    assert len(first.items) == 10
    assert [m.name for m in second.items] == ["Membro 11", "Membro 12"]

def test_member_service_page_size_and_clamping(uow):
    service = MemberService(uow)
    family = Family(name="A")
    for number in range(1, 31):
        uow.members.save(Member(family_id=family.id, name=f"Membro {number:02d}"))

    assert len(service.list_all_members_page(page_size=25).items) == 25
    assert service.list_all_members_page(page_size=13).page_size == DEFAULT_PAGE_SIZE
    assert service.list_all_members_page(page=99).page == 3

def test_cost_center_service_paginates_across_families(uow):
    service = FamilyCostCenterService(uow)
    family_a, family_b = Family(name="A"), Family(name="B")
    for number in range(1, 13):
        owner = family_a if number % 2 else family_b
        uow.family_cost_centers.save(FamilyCostCenter(family_id=owner.id, name=f"Centro {number:02d}"))

    first = service.list_all_family_cost_centers_page()
    second = service.list_all_family_cost_centers_page(page=2)

    assert (first.total, first.total_pages) == (12, 2)
    assert len(first.items) == 10
    assert [c.name for c in second.items] == ["Centro 11", "Centro 12"]

def test_cost_center_service_page_size_and_clamping(uow):
    service = FamilyCostCenterService(uow)
    family = Family(name="A")
    for number in range(1, 31):
        uow.family_cost_centers.save(FamilyCostCenter(family_id=family.id, name=f"Centro {number:02d}"))

    assert len(service.list_all_family_cost_centers_page(page_size=50).items) == 30
    assert service.list_all_family_cost_centers_page(page_size=13).page_size == DEFAULT_PAGE_SIZE
    assert service.list_all_family_cost_centers_page(page=99).page == 3
