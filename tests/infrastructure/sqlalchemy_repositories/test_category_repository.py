import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from domain.financial.entities import Category, TransactionType
from domain.shared.exceptions import EntityAlreadyExistsError
from infrastructure.database.models import TransactionModel
from infrastructure.repositories.sqlalchemy.sqlalchemy_category_repository import SQLAlchemyCategoryRepository

def test_category_repository_save_and_get(session: Session):
    repo = SQLAlchemyCategoryRepository(session)
    category = Category(name="Alimentação", type=TransactionType.EXPENSE)

    repo.save(category)
    session.flush()

    fetched = repo.get_by_id(category.id)
    assert fetched is not None
    assert (fetched.id, fetched.name, fetched.type) == (category.id, "Alimentação", TransactionType.EXPENSE)

def test_category_repository_list_all(session: Session):
    repo = SQLAlchemyCategoryRepository(session)
    repo.save(Category(name="Lazer", type=TransactionType.EXPENSE))
    repo.save(Category(name="Salário", type=TransactionType.INCOME))
    session.flush()

    assert {c.name for c in repo.list_all()} == {"Lazer", "Salário"}

def test_category_repository_save_and_delete(session: Session):
    repo = SQLAlchemyCategoryRepository(session)
    category = Category(name="A excluir", type=TransactionType.EXPENSE)
    repo.save(category)
    session.flush()

    repo.delete(category.id)
    session.flush()

    assert repo.get_by_id(category.id) is None

def test_delete_nonexistent_category_is_a_noop(session: Session):
    repo = SQLAlchemyCategoryRepository(session)
    repo.delete(uuid.uuid4())
    session.flush()

def test_get_by_name_is_case_insensitive(session: Session):
    repo = SQLAlchemyCategoryRepository(session)
    repo.save(Category(name="Saúde", type=TransactionType.EXPENSE))
    session.flush()

    fetched = repo.get_by_name("saúde")
    assert fetched is not None
    assert fetched.name == "Saúde"
    assert repo.get_by_name("Inexistente") is None

def test_save_duplicate_name_raises_already_exists_even_with_other_type(session: Session):
    repo = SQLAlchemyCategoryRepository(session)
    repo.save(Category(name="Outros", type=TransactionType.EXPENSE))
    session.flush()

    with pytest.raises(EntityAlreadyExistsError):
        repo.save(Category(name="outros", type=TransactionType.INCOME))

def test_category_without_transactions_has_no_dependencies(session: Session):
    repo = SQLAlchemyCategoryRepository(session)
    category = Category(name="Lazer", type=TransactionType.EXPENSE)
    repo.save(category)
    session.flush()

    assert repo.has_dependencies(category.id) is False

def test_category_used_by_a_transaction_has_dependencies(session: Session):
    repo = SQLAlchemyCategoryRepository(session)
    category = Category(name="Lazer", type=TransactionType.EXPENSE)
    repo.save(category)
    session.add(TransactionModel(
        id=str(uuid.uuid4()), family_id=str(uuid.uuid4()), category_id=str(category.id),
        type=TransactionType.EXPENSE, accrual_date=date(2026, 10, 1), due_date=date(2026, 10, 10),
        amount=Decimal("50.00"), description="Cinema", account_id=str(uuid.uuid4()),
    ))
    session.flush()

    assert repo.has_dependencies(category.id) is True
