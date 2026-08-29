from decimal import Decimal
from sqlalchemy.orm import Session

from domain.family.entities import Family
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