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

    with pytest.raises(EntityAlreadyExistsError):
        repo.save(Family(name="família silva"))

def test_save_rename_to_duplicate_name_raises_already_exists(session: Session):
    repo = SQLAlchemyFamilyRepository(session)
    repo.save(Family(name="Família Silva"))
    other = Family(name="Família Souza")
    repo.save(other)
    session.flush()

    other.name = "família silva"
    with pytest.raises(EntityAlreadyExistsError):
        repo.save(other)

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
