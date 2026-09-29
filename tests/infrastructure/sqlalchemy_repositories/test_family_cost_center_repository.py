import uuid
import pytest
from sqlalchemy.orm import Session

from domain.family.entities import Family, FamilyCostCenter
from domain.family.exceptions import FamilyCostCenterAlreadyExistsError
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

    with pytest.raises(FamilyCostCenterAlreadyExistsError):
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
