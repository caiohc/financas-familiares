import pytest
import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from domain.family.entities import Family
from domain.financial.entities import Category, TransactionType
from infrastructure.database.models import Base
from infrastructure.repositories.sqlalchemy_repositories import (
    SQLAlchemyFamilyRepository,
    SQLAlchemyCategoryRepository
)

# Configura um banco em memória SQLite puro apenas para os testes de infraestrutura
@pytest.fixture(scope="session")
def engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def session(engine) -> Session:
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

def test_family_repository_save_and_get(session: Session):
    repo = SQLAlchemyFamilyRepository(session)
    family = Family(name="Test Family", current_balance=Decimal("1500.50"))
    
    # Executa a ação
    repo.save(family)
    session.commit()
    
    # Busca de volta do banco
    fetched_family = repo.get_by_id(family.id)
    
    # Validações de Mapeamento
    assert fetched_family is not None
    assert fetched_family.id == family.id
    assert fetched_family.name == "Test Family"
    assert fetched_family.current_balance == Decimal("1500.50")

def test_category_repository_save_and_get(session: Session):
    repo = SQLAlchemyCategoryRepository(session)
    category = Category(name="Groceries", type=TransactionType.EXPENSE)
    
    # Executa a ação
    repo.save(category)
    session.commit()
    
    fetched = repo.get_by_id(category.id)
    
    assert fetched is not None
    assert fetched.name == "Groceries"
    assert fetched.type == TransactionType.EXPENSE
