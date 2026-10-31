from decimal import Decimal
import uuid
import pytest
from sqlalchemy.orm import Session

from domain.family.entities import Family
from domain.shared.exceptions import EntityAlreadyExistsError
from infrastructure.repositories.sqlalchemy.sqlalchemy_family_repository import SQLAlchemyFamilyRepository

def test_family_repository_save_and_get(session: Session):
    repo = SQLAlchemyFamilyRepository(session)
    family = Family(name="Test Family", current_balance=Decimal("1500.50"))
    
    # Executa a ação
    repo.save(family)
    session.flush()
    
    # Busca de volta do banco
    fetched_family = repo.get_by_id(family.id)
    
    # Validações de Mapeamento
    assert fetched_family is not None
    assert fetched_family.id == family.id
    assert fetched_family.name == "Test Family"
    assert fetched_family.current_balance == Decimal("1500.50")

def test_family_repository_save_and_list_all(session: Session):
    repo = SQLAlchemyFamilyRepository(session)
    families = []

    for i in range(1, 10 + 1):
        family = Family(name=f'Test family {i:d}', current_balance=Decimal(i * 100))
        families.append(family)
        repo.save(family)

    session.flush()

   # Lista todas as famílias
    fetched_families = repo.list_all()

    assert len(fetched_families) == len(families)

    for family in families:
        fetched_family = next((f for f in fetched_families if f.id == family.id), None)
        assert fetched_family is not None
        assert fetched_family.name == family.name
        assert fetched_family.current_balance == family.current_balance

def test_family_repository_save_and_delete(session: Session):

    repo = SQLAlchemyFamilyRepository(session)
    family = Family(name="Test Family", current_balance=Decimal("1000.00"))

    repo.save(family)
    session.flush()

    repo.delete(family.id)
    session.flush()

    fetched_family = repo.get_by_id(family.id)
    assert fetched_family is None

def test_delete_nonexistent_family_is_a_noop(session: Session):
    repo = SQLAlchemyFamilyRepository(session)

    # Repositório não conhece "não encontrada" como regra de negócio (isso é
    # responsabilidade do FamilyService); aqui só confirmamos que não explode.
    repo.delete(uuid.uuid4())
    session.flush()

def test_save_allows_families_with_the_same_name(session: Session):
    repo = SQLAlchemyFamilyRepository(session)
    first = Family(name="Família Silva")
    second = Family(name="família silva")
    repo.save(first)
    repo.save(second)
    session.flush()

    assert {f.id for f in repo.list_all()} == {first.id, second.id}

def test_family_without_dependents_has_no_dependencies(session: Session):
    repo = SQLAlchemyFamilyRepository(session)
    family = Family(name="Família Sem Deps")
    repo.save(family)
    session.flush()

    assert repo.has_dependencies(family.id) is False

def test_family_with_a_member_has_dependencies(session: Session):
    from domain.family.entities import Member
    from infrastructure.repositories.sqlalchemy.sqlalchemy_member_repository import SQLAlchemyMemberRepository

    repo = SQLAlchemyFamilyRepository(session)
    family = Family(name="Família Com Membro")
    repo.save(family)
    SQLAlchemyMemberRepository(session).save(Member(family_id=family.id, name="João"))
    session.flush()

    assert repo.has_dependencies(family.id) is True

def test_family_with_only_a_cost_center_has_dependencies(session: Session):
    from domain.family.entities import FamilyCostCenter
    from infrastructure.repositories.sqlalchemy.sqlalchemy_family_cost_center_repository import (
        SQLAlchemyFamilyCostCenterRepository,
    )

    repo = SQLAlchemyFamilyRepository(session)
    family = Family(name="Família Com Centro de Custo")
    repo.save(family)
    SQLAlchemyFamilyCostCenterRepository(session).save(FamilyCostCenter(family_id=family.id, name="Praia"))
    session.flush()

    assert repo.has_dependencies(family.id) is True

def test_dependent_table_missing_from_the_database_counts_as_no_dependency():
    # Banco real hoje: só as tabelas das fatias já migradas (sem accounts, transactions...).
    # Consultar uma tabela inexistente daria erro; sem tabela, não há registro dependente.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from infrastructure.database.models import Base

    engine = create_engine("sqlite+pysqlite:///:memory:")
    migrated = [Base.metadata.tables[name] for name in ("families", "members", "family_cost_centers")]
    Base.metadata.create_all(engine, tables=migrated)
    session = sessionmaker(bind=engine)()

    repo = SQLAlchemyFamilyRepository(session)
    family = Family(name="Família Banco Parcial")
    repo.save(family)
    session.flush()

    assert repo.has_dependencies(family.id) is False
    session.close()

# --- Paginação ---

def _save_families(session: Session, names: list[str]) -> SQLAlchemyFamilyRepository:
    repo = SQLAlchemyFamilyRepository(session)
    for name in names:
        repo.save(Family(name=name))
    session.flush()
    return repo

def test_list_page_returns_only_the_requested_slice_and_the_total(session: Session):
    repo = _save_families(session, [f"Família {n:02d}" for n in range(1, 8)])

    first = repo.list_page(page=1, page_size=3)
    last = repo.list_page(page=3, page_size=3)

    assert first.total == 7
    assert [f.name for f in first.items] == ["Família 01", "Família 02", "Família 03"]
    assert [f.name for f in last.items] == ["Família 07"]

def test_list_page_orders_by_name_ignoring_case(session: Session):
    repo = _save_families(session, ["família b", "Família C", "Família A"])

    page = repo.list_page(page=1, page_size=10)

    assert [f.name for f in page.items] == ["Família A", "família b", "Família C"]

def test_list_page_breaks_ties_between_same_named_families_deterministically(session: Session):
    repo = _save_families(session, ["Silva"] * 4)

    ids = [f.id for p in (1, 2) for f in repo.list_page(page=p, page_size=2).items]

    assert len(set(ids)) == 4

def test_list_page_beyond_the_last_page_is_empty_but_keeps_the_total(session: Session):
    repo = _save_families(session, ["Família A", "Família B"])

    page = repo.list_page(page=5, page_size=10)

    assert page.items == []
    assert page.total == 2

def test_list_page_when_empty(session: Session):
    page = SQLAlchemyFamilyRepository(session).list_page(page=1, page_size=10)

    assert page.items == []
    assert page.total == 0

# --- Ordenação ---

def test_list_page_sorts_by_name_descending(session: Session):
    repo = _save_families(session, ["família b", "Família C", "Família A"])

    page = repo.list_page(page=1, page_size=10, sort_by="name", descending=True)

    assert [f.name for f in page.items] == ["Família C", "família b", "Família A"]

def test_list_page_descending_order_spans_pages(session: Session):
    repo = _save_families(session, [f"Família {n:02d}" for n in range(1, 6)])

    first = repo.list_page(page=1, page_size=2, sort_by="name", descending=True)
    last = repo.list_page(page=3, page_size=2, sort_by="name", descending=True)

    assert [f.name for f in first.items] == ["Família 05", "Família 04"]
    assert [f.name for f in last.items] == ["Família 01"]

def test_list_page_rejects_an_unknown_sort_field(session: Session):
    repo = SQLAlchemyFamilyRepository(session)

    with pytest.raises(ValueError):
        repo.list_page(page=1, page_size=10, sort_by="balance")

# --- Pesquisa ---

def test_list_page_search_matches_part_of_the_name_ignoring_case_and_accents(session: Session):
    repo = _save_families(session, ["Família Silva", "SILVEIRA", "Família Souza", "Álvares"])

    by_case = repo.list_page(page=1, page_size=10, search="sil")
    by_accent = repo.list_page(page=1, page_size=10, search="alvares")

    assert [f.name for f in by_case.items] == ["Família Silva", "SILVEIRA"]
    assert [f.name for f in by_accent.items] == ["Álvares"]

def test_list_page_search_total_counts_only_the_matches(session: Session):
    repo = _save_families(session, ["Silva 1", "Silva 2", "Souza"])

    page = repo.list_page(page=1, page_size=10, search="silva")

    assert page.total == 2

def test_list_page_pagination_works_over_the_search_results(session: Session):
    repo = _save_families(
        session, [f"Silva {n:02d}" for n in range(1, 8)] + [f"Souza {n:02d}" for n in range(1, 20)]
    )

    first = repo.list_page(page=1, page_size=3, search="silva")
    last = repo.list_page(page=3, page_size=3, search="silva")
    beyond = repo.list_page(page=4, page_size=3, search="silva")

    assert first.total == last.total == beyond.total == 7
    assert [f.name for f in first.items] == ["Silva 01", "Silva 02", "Silva 03"]
    assert [f.name for f in last.items] == ["Silva 07"]
    assert beyond.items == []

def test_list_page_search_keeps_the_sort_order(session: Session):
    repo = _save_families(session, ["Silva B", "Souza", "Silva A", "Silva C"])

    page = repo.list_page(page=1, page_size=10, sort_by="name", descending=True, search="silva")

    assert [f.name for f in page.items] == ["Silva C", "Silva B", "Silva A"]

def test_list_page_search_without_matches_is_empty(session: Session):
    repo = _save_families(session, ["Silva"])

    page = repo.list_page(page=1, page_size=10, search="xyz")

    assert page.items == []
    assert page.total == 0

@pytest.mark.parametrize("term", ["%", "_", "\\"])
def test_list_page_search_treats_wildcards_as_plain_text(session: Session, term):
    repo = _save_families(session, ["Silva", "Souza", "100% Silva"])

    page = repo.list_page(page=1, page_size=10, search=term)

    assert [f.name for f in page.items] == (["100% Silva"] if term == "%" else [])

@pytest.mark.parametrize("search", [None, ""])
def test_list_page_without_search_returns_everything(session: Session, search):
    repo = _save_families(session, ["Silva", "Souza"])

    assert repo.list_page(page=1, page_size=10, search=search).total == 2
