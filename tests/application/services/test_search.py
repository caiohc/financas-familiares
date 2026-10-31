"""Pesquisa nas listagens paginadas: o resultado vira a lista sobre a qual a paginação opera."""
import pytest

from application.services.family_service import FamilyService
from application.services.family_cost_center_service import FamilyCostCenterService
from application.services.member_service import MemberService
from domain.family.entities import Family, FamilyCostCenter, Member
from fakes.family_fakes import FakeUnitOfWork

@pytest.fixture
def uow():
    return FakeUnitOfWork()

def _names(result):
    return [item.name for item in result.items]

def _seed_families(uow, silvas: int, others: int) -> None:
    for n in range(1, silvas + 1):
        uow.families.save(Family(name=f"Silva {n:02d}"))
    for n in range(1, others + 1):
        uow.families.save(Family(name=f"Souza {n:02d}"))

def test_search_filters_the_listing_and_is_reported_back(uow):
    _seed_families(uow, silvas=3, others=2)

    result = FamilyService(uow).list_families_page(search="silva")

    assert result.search == "silva"
    assert _names(result) == ["Silva 01", "Silva 02", "Silva 03"]
    assert result.total == 3

def test_no_search_means_no_filter(uow):
    _seed_families(uow, silvas=2, others=2)

    result = FamilyService(uow).list_families_page()

    assert result.search == ""
    assert result.total == 4

@pytest.mark.parametrize("raw", ["", "   ", None])
def test_blank_search_is_the_same_as_no_search(uow, raw):
    _seed_families(uow, silvas=2, others=2)

    result = FamilyService(uow).list_families_page(search=raw)

    assert result.search == ""
    assert result.total == 4

def test_search_is_stripped(uow):
    _seed_families(uow, silvas=2, others=2)

    result = FamilyService(uow).list_families_page(search="  silva  ")

    assert result.search == "silva"
    assert result.total == 2

def test_search_term_is_capped_to_a_reasonable_length(uow):
    _seed_families(uow, silvas=1, others=0)

    result = FamilyService(uow).list_families_page(search="a" * 500)

    assert len(result.search) == 100

def test_pagination_counts_pages_over_the_search_results_not_the_whole_table(uow):
    _seed_families(uow, silvas=25, others=40)

    result = FamilyService(uow).list_families_page(search="silva")

    assert result.total == 25
    assert result.total_pages == 3
    assert len(result.items) == 10
    assert result.has_next is True

def test_paging_through_the_search_results_reaches_only_the_matches(uow):
    _seed_families(uow, silvas=25, others=40)
    service = FamilyService(uow)

    pages = [service.list_families_page(page=p, search="silva") for p in (1, 2, 3)]

    assert [len(p.items) for p in pages] == [10, 10, 5]
    assert all("Silva" in name for p in pages for name in _names(p))
    assert pages[2].has_next is False

def test_page_beyond_the_last_page_of_the_results_returns_the_last_page_of_the_results(uow):
    _seed_families(uow, silvas=25, others=40)

    result = FamilyService(uow).list_families_page(page=7, search="silva")

    assert result.page == 3
    assert len(result.items) == 5

def test_search_without_results_has_one_empty_page(uow):
    _seed_families(uow, silvas=3, others=0)

    result = FamilyService(uow).list_families_page(page=2, search="xyz")

    assert (result.page, result.total, result.total_pages) == (1, 0, 1)
    assert result.items == []

def test_search_keeps_page_size_and_sorting(uow):
    _seed_families(uow, silvas=30, others=5)

    result = FamilyService(uow).list_families_page(page_size=25, sort_dir="desc", search="silva")

    assert result.page_size == 25
    assert len(result.items) == 25
    assert result.items[0].name == "Silva 30"

def test_member_search_covers_member_name_and_family_name(uow):
    silva, souza = Family(name="Silva"), Family(name="Souza")
    uow.families.save(silva)
    uow.families.save(souza)
    uow.members.save(Member(family_id=silva.id, name="Ana"))
    uow.members.save(Member(family_id=souza.id, name="Silvio"))
    uow.members.save(Member(family_id=souza.id, name="Bruno"))

    result = MemberService(uow).list_all_members_page(search="silv")

    assert _names(result) == ["Ana", "Silvio"]
    assert result.search == "silv"

def test_member_pagination_over_the_search_results(uow):
    silva, souza = Family(name="Silva"), Family(name="Souza")
    uow.families.save(silva)
    uow.families.save(souza)
    for n in range(1, 13):
        uow.members.save(Member(family_id=silva.id, name=f"Membro {n:02d}"))
    for n in range(13, 40):
        uow.members.save(Member(family_id=souza.id, name=f"Membro {n:02d}"))

    second = MemberService(uow).list_all_members_page(page=2, search="silva")

    assert (second.total, second.total_pages) == (12, 2)
    assert _names(second) == ["Membro 11", "Membro 12"]

def test_cost_center_search_covers_name_and_family_name(uow):
    silva, souza = Family(name="Silva"), Family(name="Souza")
    uow.families.save(silva)
    uow.families.save(souza)
    uow.family_cost_centers.save(FamilyCostCenter(family_id=silva.id, name="Escola"))
    uow.family_cost_centers.save(FamilyCostCenter(family_id=souza.id, name="Escolinha de futebol"))
    uow.family_cost_centers.save(FamilyCostCenter(family_id=souza.id, name="Filhos"))

    by_name = FamilyCostCenterService(uow).list_all_family_cost_centers_page(search="escol")
    by_family = FamilyCostCenterService(uow).list_all_family_cost_centers_page(search="silva")

    assert _names(by_name) == ["Escola", "Escolinha de futebol"]
    assert _names(by_family) == ["Escola"]

def test_cost_center_pagination_over_the_search_results(uow):
    silva, souza = Family(name="Silva"), Family(name="Souza")
    uow.families.save(silva)
    uow.families.save(souza)
    for n in range(1, 13):
        uow.family_cost_centers.save(FamilyCostCenter(family_id=silva.id, name=f"Centro {n:02d}"))
    for n in range(13, 40):
        uow.family_cost_centers.save(FamilyCostCenter(family_id=souza.id, name=f"Centro {n:02d}"))

    second = FamilyCostCenterService(uow).list_all_family_cost_centers_page(page=2, search="silva")

    assert (second.total, second.total_pages) == (12, 2)
    assert _names(second) == ["Centro 11", "Centro 12"]
