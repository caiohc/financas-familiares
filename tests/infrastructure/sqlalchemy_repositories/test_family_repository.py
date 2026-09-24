from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from domain.family.entities import Family
from domain.family.exceptions import FamilyAlreadyExistsError
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

def test_get_by_name_is_case_insensitive(session: Session):
    repo = SQLAlchemyFamilyRepository(session)
    repo.save(Family(name="Família Silva"))
    session.flush()

    fetched = repo.get_by_name("família silva")

    assert fetched is not None
    assert fetched.name == "Família Silva"

def test_get_by_name_returns_none_when_absent(session: Session):
    repo = SQLAlchemyFamilyRepository(session)
    assert repo.get_by_name("Família Inexistente") is None

def test_save_duplicate_name_raises_already_exists(session: Session):
    repo = SQLAlchemyFamilyRepository(session)
    repo.save(Family(name="Família Silva"))
    session.flush()

    with pytest.raises(FamilyAlreadyExistsError):
        repo.save(Family(name="família silva"))
