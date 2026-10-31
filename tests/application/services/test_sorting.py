"""Regras de ordenação das listagens paginadas (Família, Membro e Centro de Custo)."""
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

def test_family_list_defaults_to_name_ascending(uow):
    for name in ("família b", "Família C", "Família A"):
        uow.families.save(Family(name=name))

    result = FamilyService(uow).list_families_page()

    assert (result.sort_by, result.sort_dir) == ("name", "asc")
    assert _names(result) == ["Família A", "família b", "Família C"]

def test_family_list_sorts_descending(uow):
    for name in ("Família A", "Família B", "Família C"):
        uow.families.save(Family(name=name))

    result = FamilyService(uow).list_families_page(sort_by="name", sort_dir="desc")

    assert (result.sort_by, result.sort_dir) == ("name", "desc")
    assert _names(result) == ["Família C", "Família B", "Família A"]

@pytest.mark.parametrize("sort_by", ["family", "balance", "", "NAME", None])
def test_family_list_only_sorts_by_name(uow, sort_by):
    uow.families.save(Family(name="Família A"))

    result = FamilyService(uow).list_families_page(sort_by=sort_by)

    assert result.sort_by == "name"

@pytest.mark.parametrize("sort_dir", ["up", "", "DESC", 1, None])
def test_invalid_direction_falls_back_to_ascending(uow, sort_dir):
    for name in ("Família A", "Família B"):
        uow.families.save(Family(name=name))

    result = FamilyService(uow).list_families_page(sort_dir=sort_dir)

    assert result.sort_dir == "asc"
    assert _names(result) == ["Família A", "Família B"]

def test_sorting_applies_before_pagination(uow):
    for number in range(1, 16):
        uow.families.save(Family(name=f"Família {number:02d}"))

    result = FamilyService(uow).list_families_page(page=2, sort_dir="desc")

    assert _names(result) == [f"Família {n:02d}" for n in range(5, 0, -1)]

def _seed_members(uow):
    souza, almeida = Family(name="souza"), Family(name="Almeida")
    uow.families.save(souza)
    uow.families.save(almeida)
    uow.members.save(Member(family_id=souza.id, name="Ana"))
    uow.members.save(Member(family_id=almeida.id, name="Zélia"))
    uow.members.save(Member(family_id=almeida.id, name="Bruno"))

def test_member_list_defaults_to_name_ascending(uow):
    _seed_members(uow)

    result = MemberService(uow).list_all_members_page()

    assert (result.sort_by, result.sort_dir) == ("name", "asc")
    assert _names(result) == ["Ana", "Bruno", "Zélia"]

def test_member_list_sorts_by_family_name(uow):
    _seed_members(uow)

    result = MemberService(uow).list_all_members_page(sort_by="family")
    descending = MemberService(uow).list_all_members_page(sort_by="family", sort_dir="desc")

    assert result.sort_by == "family"
    assert _names(result) == ["Bruno", "Zélia", "Ana"]
    assert _names(descending) == ["Ana", "Bruno", "Zélia"]

def test_member_list_rejects_unknown_sort_field(uow):
    _seed_members(uow)

    assert MemberService(uow).list_all_members_page(sort_by="id").sort_by == "name"

def test_cost_center_list_sorts_by_name_and_by_family_name(uow):
    souza, almeida = Family(name="souza"), Family(name="Almeida")
    uow.families.save(souza)
    uow.families.save(almeida)
    uow.family_cost_centers.save(FamilyCostCenter(family_id=souza.id, name="Escola"))
    uow.family_cost_centers.save(FamilyCostCenter(family_id=almeida.id, name="Praia"))
    uow.family_cost_centers.save(FamilyCostCenter(family_id=almeida.id, name="Filhos"))
    service = FamilyCostCenterService(uow)

    by_name = service.list_all_family_cost_centers_page()
    by_family = service.list_all_family_cost_centers_page(sort_by="family")
    by_family_desc = service.list_all_family_cost_centers_page(sort_by="family", sort_dir="desc")

    assert (by_name.sort_by, by_name.sort_dir) == ("name", "asc")
    assert _names(by_name) == ["Escola", "Filhos", "Praia"]
    assert _names(by_family) == ["Filhos", "Praia", "Escola"]
    assert _names(by_family_desc) == ["Escola", "Filhos", "Praia"]

def test_cost_center_list_rejects_unknown_sort_field(uow):
    uow.family_cost_centers.save(FamilyCostCenter(family_id=Family(name="A").id, name="Escola"))

    result = FamilyCostCenterService(uow).list_all_family_cost_centers_page(sort_by="description")

    assert result.sort_by == "name"
