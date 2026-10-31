import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from domain.family.entities import Family, Member
from domain.financial.entities import AccountType
from domain.shared.exceptions import EntityAlreadyExistsError
from infrastructure.database.models import AccountModel
from infrastructure.repositories.sqlalchemy.sqlalchemy_family_repository import SQLAlchemyFamilyRepository
from infrastructure.repositories.sqlalchemy.sqlalchemy_member_repository import SQLAlchemyMemberRepository

def _create_family(session: Session, name: str) -> Family:
    family = Family(name=name)
    SQLAlchemyFamilyRepository(session).save(family)
    session.flush()
    return family

def test_member_repository_save_and_get(session: Session):
    family = _create_family(session, "Família Um")
    repo = SQLAlchemyMemberRepository(session)
    member = Member(family_id=family.id, name="João")

    repo.save(member)
    session.flush()

    fetched = repo.get_by_id(member.id)
    assert fetched is not None
    assert fetched.id == member.id
    assert fetched.family_id == family.id
    assert fetched.name == "João"

def test_member_repository_list_by_family(session: Session):
    family_a = _create_family(session, "Família A")
    family_b = _create_family(session, "Família B")
    repo = SQLAlchemyMemberRepository(session)
    repo.save(Member(family_id=family_a.id, name="João"))
    repo.save(Member(family_id=family_a.id, name="Maria"))
    repo.save(Member(family_id=family_b.id, name="Pedro"))
    session.flush()

    assert {m.name for m in repo.list_by_family(family_a.id)} == {"João", "Maria"}

def test_member_repository_list_all_returns_members_across_families(session: Session):
    family_a = _create_family(session, "Família All A")
    family_b = _create_family(session, "Família All B")
    repo = SQLAlchemyMemberRepository(session)
    repo.save(Member(family_id=family_a.id, name="João"))
    repo.save(Member(family_id=family_b.id, name="Pedro"))
    session.flush()

    assert {m.name for m in repo.list_all()} == {"João", "Pedro"}

def test_member_repository_save_and_delete(session: Session):
    family = _create_family(session, "Família Delete")
    repo = SQLAlchemyMemberRepository(session)
    member = Member(family_id=family.id, name="A excluir")
    repo.save(member)
    session.flush()

    repo.delete(member.id)
    session.flush()

    assert repo.get_by_id(member.id) is None

def test_delete_nonexistent_member_is_a_noop(session: Session):
    repo = SQLAlchemyMemberRepository(session)
    repo.delete(uuid.uuid4())
    session.flush()

def test_get_by_name_is_case_insensitive_and_scoped_to_family(session: Session):
    family = _create_family(session, "Família Case")
    other = _create_family(session, "Família Outra")
    repo = SQLAlchemyMemberRepository(session)
    repo.save(Member(family_id=family.id, name="João"))
    session.flush()

    fetched = repo.get_by_name(family.id, "joão")
    assert fetched is not None
    assert fetched.name == "João"
    assert repo.get_by_name(other.id, "João") is None

def test_save_duplicate_name_in_same_family_raises_already_exists(session: Session):
    family = _create_family(session, "Família Dup")
    repo = SQLAlchemyMemberRepository(session)
    repo.save(Member(family_id=family.id, name="João"))
    session.flush()

    with pytest.raises(EntityAlreadyExistsError):
        repo.save(Member(family_id=family.id, name="joão"))

def test_save_same_name_in_different_families_is_allowed(session: Session):
    family_a = _create_family(session, "Família Cross A")
    family_b = _create_family(session, "Família Cross B")
    repo = SQLAlchemyMemberRepository(session)
    repo.save(Member(family_id=family_a.id, name="João"))
    repo.save(Member(family_id=family_b.id, name="João"))
    session.flush()

    assert len(repo.list_by_family(family_a.id)) == 1
    assert len(repo.list_by_family(family_b.id)) == 1

def test_member_without_dependents_has_no_dependencies(session: Session):
    family = _create_family(session, "Família Sem Deps")
    repo = SQLAlchemyMemberRepository(session)
    member = Member(family_id=family.id, name="João")
    repo.save(member)
    session.flush()

    assert repo.has_dependencies(member.id) is False

def test_member_holding_an_account_has_dependencies(session: Session):
    family = _create_family(session, "Família Com Conta")
    repo = SQLAlchemyMemberRepository(session)
    member = Member(family_id=family.id, name="João")
    repo.save(member)
    session.add(AccountModel(
        id=str(uuid.uuid4()), family_id=str(family.id), holder_id=str(member.id),
        nickname="Conta", account_type=AccountType.ASSET, current_balance=Decimal("0.00"),
    ))
    session.flush()

    assert repo.has_dependencies(member.id) is True

# --- Paginação ---

def test_member_list_page_slices_across_families_and_reports_the_total(session: Session):
    family_a = _create_family(session, "Família A")
    family_b = _create_family(session, "Família B")
    repo = SQLAlchemyMemberRepository(session)
    for index in range(1, 6):
        owner = family_a if index % 2 else family_b
        repo.save(Member(family_id=owner.id, name=f"Membro {index}"))
    session.flush()

    first = repo.list_page(page=1, page_size=2)
    last = repo.list_page(page=3, page_size=2)

    assert first.total == 5
    assert [m.name for m in first.items] == ["Membro 1", "Membro 2"]
    assert [m.name for m in last.items] == ["Membro 5"]

def test_member_list_page_orders_by_name_ignoring_case(session: Session):
    family = _create_family(session, "Família A")
    repo = SQLAlchemyMemberRepository(session)
    for name in ("maria", "Ana", "João"):
        repo.save(Member(family_id=family.id, name=name))
    session.flush()

    page = repo.list_page(page=1, page_size=10)

    assert [m.name for m in page.items] == ["Ana", "João", "maria"]

def test_member_list_page_beyond_the_last_page_is_empty_but_keeps_the_total(session: Session):
    family = _create_family(session, "Família A")
    repo = SQLAlchemyMemberRepository(session)
    repo.save(Member(family_id=family.id, name="João"))
    session.flush()

    page = repo.list_page(page=4, page_size=10)

    assert page.items == []
    assert page.total == 1

# --- Ordenação ---

def _seed_members_for_sorting(session: Session) -> SQLAlchemyMemberRepository:
    souza = _create_family(session, "souza")
    almeida = _create_family(session, "Almeida")
    repo = SQLAlchemyMemberRepository(session)
    repo.save(Member(family_id=souza.id, name="Ana"))
    repo.save(Member(family_id=almeida.id, name="Zélia"))
    repo.save(Member(family_id=almeida.id, name="Bruno"))
    session.flush()
    return repo

def test_member_list_page_sorts_by_name_descending(session: Session):
    repo = _seed_members_for_sorting(session)

    page = repo.list_page(page=1, page_size=10, sort_by="name", descending=True)

    assert [m.name for m in page.items] == ["Zélia", "Bruno", "Ana"]

def test_member_list_page_sorts_by_family_name_ignoring_case_then_member_name(session: Session):
    repo = _seed_members_for_sorting(session)

    page = repo.list_page(page=1, page_size=10, sort_by="family")

    assert [m.name for m in page.items] == ["Bruno", "Zélia", "Ana"]

def test_member_list_page_sorts_by_family_name_descending_keeping_member_names_ascending(session: Session):
    repo = _seed_members_for_sorting(session)

    page = repo.list_page(page=1, page_size=10, sort_by="family", descending=True)

    assert [m.name for m in page.items] == ["Ana", "Bruno", "Zélia"]

def test_member_list_page_sorted_by_family_still_reports_the_full_total(session: Session):
    repo = _seed_members_for_sorting(session)

    page = repo.list_page(page=2, page_size=2, sort_by="family")

    assert page.total == 3
    assert [m.name for m in page.items] == ["Ana"]

def test_member_list_page_rejects_an_unknown_sort_field(session: Session):
    repo = SQLAlchemyMemberRepository(session)

    with pytest.raises(ValueError):
        repo.list_page(page=1, page_size=10, sort_by="balance")

# --- Pesquisa ---

def _seed_members_for_search(session: Session) -> SQLAlchemyMemberRepository:
    silva = _create_family(session, "Família Silva")
    souza = _create_family(session, "Família Souza")
    repo = SQLAlchemyMemberRepository(session)
    repo.save(Member(family_id=silva.id, name="Ana"))
    repo.save(Member(family_id=silva.id, name="José"))
    repo.save(Member(family_id=souza.id, name="Silvio"))
    repo.save(Member(family_id=souza.id, name="Bruno"))
    session.flush()
    return repo

def test_member_search_matches_the_member_name_or_the_family_name(session: Session):
    repo = _seed_members_for_search(session)

    page = repo.list_page(page=1, page_size=10, search="silv")

    # Ana e José (família Silva) pelo nome da família; Silvio pelo próprio nome
    assert [m.name for m in page.items] == ["Ana", "José", "Silvio"]
    assert page.total == 3

def test_member_search_ignores_case_and_accents(session: Session):
    repo = _seed_members_for_search(session)

    assert [m.name for m in repo.list_page(page=1, page_size=10, search="JOSE").items] == ["José"]

def test_member_search_does_not_duplicate_a_member_matching_in_both_fields(session: Session):
    family = _create_family(session, "Silva")
    repo = SQLAlchemyMemberRepository(session)
    repo.save(Member(family_id=family.id, name="Silvia"))
    session.flush()

    page = repo.list_page(page=1, page_size=10, search="sil")

    assert page.total == 1
    assert len(page.items) == 1

def test_member_pagination_works_over_the_search_results(session: Session):
    silva = _create_family(session, "Silva")
    souza = _create_family(session, "Souza")
    repo = SQLAlchemyMemberRepository(session)
    for n in range(1, 6):
        repo.save(Member(family_id=silva.id, name=f"Membro {n}"))
    for n in range(6, 16):
        repo.save(Member(family_id=souza.id, name=f"Membro {n}"))
    session.flush()

    first = repo.list_page(page=1, page_size=2, search="silva")
    last = repo.list_page(page=3, page_size=2, search="silva")

    assert first.total == last.total == 5
    assert [m.name for m in first.items] == ["Membro 1", "Membro 2"]
    assert [m.name for m in last.items] == ["Membro 5"]

def test_member_search_combines_with_sort_by_family(session: Session):
    repo = _seed_members_for_search(session)

    page = repo.list_page(page=1, page_size=10, sort_by="family", descending=True, search="silv")

    assert [m.name for m in page.items] == ["Silvio", "Ana", "José"]
