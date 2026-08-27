from sqlalchemy.orm import Session
from domain.financial.entities import Category, TransactionType
from infrastructure.repositories.sqlalchemy_repositories import SQLAlchemyCategoryRepository

def test_category_repository_save_and_get(session: Session):
    repo = SQLAlchemyCategoryRepository(session)
    category = Category(name="Groceries", type=TransactionType.EXPENSE)
    
    # Executa a ação
    repo.save(category)
    session.flush()
    
    fetched = repo.get_by_id(category.id)
    
    assert fetched is not None
    assert fetched.name == "Groceries"
    assert fetched.type == TransactionType.EXPENSE
