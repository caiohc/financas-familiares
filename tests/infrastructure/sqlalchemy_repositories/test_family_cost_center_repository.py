import uuid
import pytest
from sqlalchemy.orm import Session

from domain.family.entities import Family, FamilyCostCenter
from domain.shared.exceptions import EntityAlreadyExistsError
from infrastructure.repositories.sqlalchemy.sqlalchemy_family_repository import SQLAlchemyFamilyRepository
from infrastructure.repositories.sqlalchemy.sqlalchemy_family_cost_center_repository import (
    SQLAlchemyFamilyCostCenterRepository,
)

def _create_family(session: Session, name: str) -> Family:
    family = Family(name=name)
    SQLAlchemyFamilyRepository(session).save(family)
    session.flush()
    return family

def test_family_cost_center_repository_save_and_get(session: Session):
    family = _create_family(session, "Família Um")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    cost_center = FamilyCostCenter(family_id=family.id, name="Casa de Praia", description="Litoral")

    repo.save(cost_center)
    session.flush()

    fetched = repo.get_by_id(cost_center.id)
    assert fetched is not None
    assert fetched.family_id == family.id
    assert fetched.name == "Casa de Praia"
    assert fetched.description == "Litoral"

def test_family_cost_center_repository_list_by_family(session: Session):
    family_a = _create_family(session, "Família A")
    family_b = _create_family(session, "Família B")
    repo = SQLAlchemyFamilyCostCenterRepository(session)

    repo.save(FamilyCostCenter(family_id=family_a.id, name="Casa de Praia"))
    repo.save(FamilyCostCenter(family_id=family_a.id, name="Filhos"))
    repo.save(FamilyCostCenter(family_id=family_b.id, name="Outro"))
    session.flush()

    result = repo.list_by_family(family_a.id)
    assert {cc.name for cc in result} == {"Casa de Praia", "Filhos"}

def test_family_cost_center_repository_save_and_delete(session: Session):
    family = _create_family(session, "Família Delete")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    cost_center = FamilyCostCenter(family_id=family.id, name="A deletar")

    repo.save(cost_center)
    session.flush()

    repo.delete(cost_center.id)
    session.flush()

    assert repo.get_by_id(cost_center.id) is None

def test_delete_nonexistent_cost_center_is_a_noop(session: Session):
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    repo.delete(uuid.uuid4())
    session.flush()

def test_get_by_name_is_case_insensitive_and_scoped_to_family(session: Session):
    family = _create_family(session, "Família Case")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    repo.save(FamilyCostCenter(family_id=family.id, name="Casa de Praia"))
    session.flush()

    fetched = repo.get_by_name(family.id, "casa de praia")
    assert fetched is not None
    assert fetched.name == "Casa de Praia"

def test_get_by_name_does_not_leak_across_families(session: Session):
    family_a = _create_family(session, "Família X")
    family_b = _create_family(session, "Família Y")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    repo.save(FamilyCostCenter(family_id=family_a.id, name="Casa de Praia"))
    session.flush()

    assert repo.get_by_name(family_b.id, "Casa de Praia") is None

def test_save_duplicate_name_in_same_family_raises_already_exists(session: Session):
    family = _create_family(session, "Família Dup")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    repo.save(FamilyCostCenter(family_id=family.id, name="Casa de Praia"))
    session.flush()

    with pytest.raises(EntityAlreadyExistsError):
        repo.save(FamilyCostCenter(family_id=family.id, name="casa de praia"))

def test_save_same_name_in_different_families_is_allowed(session: Session):
    family_a = _create_family(session, "Família Cross A")
    family_b = _create_family(session, "Família Cross B")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    repo.save(FamilyCostCenter(family_id=family_a.id, name="Casa de Praia"))
    session.flush()

    # Não deve levantar: mesmo nome, famílias diferentes.
    repo.save(FamilyCostCenter(family_id=family_b.id, name="Casa de Praia"))
    session.flush()

    assert len(repo.list_by_family(family_a.id)) == 1
    assert len(repo.list_by_family(family_b.id)) == 1

def test_list_all_returns_cost_centers_across_families(session: Session):
    family_a = _create_family(session, "Família All A")
    family_b = _create_family(session, "Família All B")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    repo.save(FamilyCostCenter(family_id=family_a.id, name="Casa de Praia"))
    repo.save(FamilyCostCenter(family_id=family_b.id, name="Filhos"))
    session.flush()

    result = repo.list_all()
    assert {cc.name for cc in result} == {"Casa de Praia", "Filhos"}

def test_cost_center_without_transactions_has_no_dependencies(session: Session):
    family = _create_family(session, "Família CC Sem Deps")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    cost_center = FamilyCostCenter(family_id=family.id, name="Praia")
    repo.save(cost_center)
    session.flush()

    assert repo.has_dependencies(cost_center.id) is False

def test_cost_center_used_by_a_transaction_has_dependencies(session: Session):
    from datetime import date
    from decimal import Decimal
    from domain.financial.entities import TransactionType
    from infrastructure.database.models import TransactionModel

    family = _create_family(session, "Família CC Com Transação")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    cost_center = FamilyCostCenter(family_id=family.id, name="Praia")
    repo.save(cost_center)
    session.add(TransactionModel(
        id=str(uuid.uuid4()), family_id=str(family.id), category_id=str(uuid.uuid4()),
        type=TransactionType.EXPENSE, accrual_date=date(2026, 10, 1), due_date=date(2026, 10, 10),
        amount=Decimal("10.00"), description="Sorvete", account_id=str(uuid.uuid4()),
        cost_center_id=str(cost_center.id),
    ))
    session.flush()

    assert repo.has_dependencies(cost_center.id) is True

# --- Paginação ---

def test_cost_center_list_page_slices_across_families_and_reports_the_total(session: Session):
    family_a = _create_family(session, "Família A")
    family_b = _create_family(session, "Família B")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    for index in range(1, 6):
        owner = family_a if index % 2 else family_b
        repo.save(FamilyCostCenter(family_id=owner.id, name=f"Centro {index}"))
    session.flush()

    first = repo.list_page(page=1, page_size=2)
    last = repo.list_page(page=3, page_size=2)

    assert first.total == 5
    assert [c.name for c in first.items] == ["Centro 1", "Centro 2"]
    assert [c.name for c in last.items] == ["Centro 5"]

def test_cost_center_list_page_orders_by_name_ignoring_case(session: Session):
    family = _create_family(session, "Família A")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    for name in ("filhos", "Casa de Praia", "Escola"):
        repo.save(FamilyCostCenter(family_id=family.id, name=name))
    session.flush()

    page = repo.list_page(page=1, page_size=10)

    assert [c.name for c in page.items] == ["Casa de Praia", "Escola", "filhos"]

def test_cost_center_list_page_beyond_the_last_page_is_empty_but_keeps_the_total(session: Session):
    family = _create_family(session, "Família A")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    repo.save(FamilyCostCenter(family_id=family.id, name="Casa de Praia"))
    session.flush()

    page = repo.list_page(page=4, page_size=10)

    assert page.items == []
    assert page.total == 1

# --- Ordenação ---

def _seed_cost_centers_for_sorting(session: Session) -> SQLAlchemyFamilyCostCenterRepository:
    souza = _create_family(session, "souza")
    almeida = _create_family(session, "Almeida")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    repo.save(FamilyCostCenter(family_id=souza.id, name="Escola"))
    repo.save(FamilyCostCenter(family_id=almeida.id, name="Praia"))
    repo.save(FamilyCostCenter(family_id=almeida.id, name="Filhos"))
    session.flush()
    return repo

def test_cost_center_list_page_sorts_by_name_descending(session: Session):
    repo = _seed_cost_centers_for_sorting(session)

    page = repo.list_page(page=1, page_size=10, sort_by="name", descending=True)

    assert [c.name for c in page.items] == ["Praia", "Filhos", "Escola"]

def test_cost_center_list_page_sorts_by_family_name_ignoring_case_then_name(session: Session):
    repo = _seed_cost_centers_for_sorting(session)

    page = repo.list_page(page=1, page_size=10, sort_by="family")

    assert [c.name for c in page.items] == ["Filhos", "Praia", "Escola"]

def test_cost_center_list_page_sorts_by_family_name_descending_keeping_names_ascending(session: Session):
    repo = _seed_cost_centers_for_sorting(session)

    page = repo.list_page(page=1, page_size=10, sort_by="family", descending=True)

    assert [c.name for c in page.items] == ["Escola", "Filhos", "Praia"]

def test_cost_center_list_page_sorted_by_family_still_reports_the_full_total(session: Session):
    repo = _seed_cost_centers_for_sorting(session)

    page = repo.list_page(page=2, page_size=2, sort_by="family")

    assert page.total == 3
    assert [c.name for c in page.items] == ["Escola"]

def test_cost_center_list_page_rejects_an_unknown_sort_field(session: Session):
    repo = SQLAlchemyFamilyCostCenterRepository(session)

    with pytest.raises(ValueError):
        repo.list_page(page=1, page_size=10, sort_by="description")

# --- Pesquisa ---

def _seed_cost_centers_for_search(session: Session) -> SQLAlchemyFamilyCostCenterRepository:
    silva = _create_family(session, "Família Silva")
    souza = _create_family(session, "Família Souza")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    repo.save(FamilyCostCenter(family_id=silva.id, name="Casa de Praia"))
    repo.save(FamilyCostCenter(family_id=silva.id, name="Escola"))
    repo.save(FamilyCostCenter(family_id=souza.id, name="Praia Grande"))
    repo.save(FamilyCostCenter(family_id=souza.id, name="Filhos"))
    session.flush()
    return repo

def test_cost_center_search_matches_the_name_or_the_family_name(session: Session):
    repo = _seed_cost_centers_for_search(session)

    by_name = repo.list_page(page=1, page_size=10, search="praia")
    by_family = repo.list_page(page=1, page_size=10, search="silva")

    assert [c.name for c in by_name.items] == ["Casa de Praia", "Praia Grande"]
    assert [c.name for c in by_family.items] == ["Casa de Praia", "Escola"]

def test_cost_center_search_ignores_case_and_accents(session: Session):
    family = _create_family(session, "Família Silva")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    repo.save(FamilyCostCenter(family_id=family.id, name="Educação"))
    session.flush()

    assert [c.name for c in repo.list_page(page=1, page_size=10, search="EDUCACAO").items] == ["Educação"]

def test_cost_center_pagination_works_over_the_search_results(session: Session):
    silva = _create_family(session, "Silva")
    souza = _create_family(session, "Souza")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    for n in range(1, 6):
        repo.save(FamilyCostCenter(family_id=silva.id, name=f"Centro {n}"))
    for n in range(6, 16):
        repo.save(FamilyCostCenter(family_id=souza.id, name=f"Centro {n}"))
    session.flush()

    first = repo.list_page(page=1, page_size=2, search="silva")
    last = repo.list_page(page=3, page_size=2, search="silva")

    assert first.total == last.total == 5
    assert [c.name for c in first.items] == ["Centro 1", "Centro 2"]
    assert [c.name for c in last.items] == ["Centro 5"]

def test_cost_center_search_does_not_duplicate_a_match_in_both_fields(session: Session):
    family = _create_family(session, "Praia")
    repo = SQLAlchemyFamilyCostCenterRepository(session)
    repo.save(FamilyCostCenter(family_id=family.id, name="Casa de Praia"))
    session.flush()

    page = repo.list_page(page=1, page_size=10, search="praia")

    assert page.total == 1 and len(page.items) == 1
