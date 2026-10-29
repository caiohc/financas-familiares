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
