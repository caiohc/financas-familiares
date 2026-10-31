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

# --- Paginação, ordenação e pesquisa ---

def _seed_categories(session: Session) -> SQLAlchemyCategoryRepository:
    repo = SQLAlchemyCategoryRepository(session)
    repo.save(Category(name="lazer", type=TransactionType.EXPENSE))
    repo.save(Category(name="Salário", type=TransactionType.INCOME))
    repo.save(Category(name="Alimentação", type=TransactionType.EXPENSE))
    repo.save(Category(name="Freelance", type=TransactionType.INCOME))
    session.flush()
    return repo

def test_category_list_page_slices_and_reports_the_total(session: Session):
    repo = _seed_categories(session)

    first = repo.list_page(page=1, page_size=3)
    last = repo.list_page(page=2, page_size=3)

    assert first.total == 4
    assert [c.name for c in first.items] == ["Alimentação", "Freelance", "lazer"]
    assert [c.name for c in last.items] == ["Salário"]

def test_category_list_page_sorts_by_name_descending(session: Session):
    repo = _seed_categories(session)

    page = repo.list_page(page=1, page_size=10, sort_by="name", descending=True)

    assert [c.name for c in page.items] == ["Salário", "lazer", "Freelance", "Alimentação"]

def test_category_list_page_sorts_by_type_then_name(session: Session):
    repo = _seed_categories(session)

    ascending = repo.list_page(page=1, page_size=10, sort_by="type")
    descending = repo.list_page(page=1, page_size=10, sort_by="type", descending=True)

    assert [c.name for c in ascending.items] == ["Alimentação", "lazer", "Freelance", "Salário"]
    assert [c.name for c in descending.items] == ["Freelance", "Salário", "Alimentação", "lazer"]

def test_category_list_page_rejects_an_unknown_sort_field(session: Session):
    repo = SQLAlchemyCategoryRepository(session)

    with pytest.raises(ValueError):
        repo.list_page(page=1, page_size=10, sort_by="id")

def test_category_search_matches_the_name_ignoring_case_and_accents(session: Session):
    repo = _seed_categories(session)

    assert [c.name for c in repo.list_page(page=1, page_size=10, search="SALARIO").items] == ["Salário"]

def test_category_search_matches_the_type_label(session: Session):
    repo = _seed_categories(session)

    expenses = repo.list_page(page=1, page_size=10, search="desp")
    incomes = repo.list_page(page=1, page_size=10, search="RECEITA")

    assert [c.name for c in expenses.items] == ["Alimentação", "lazer"]
    assert [c.name for c in incomes.items] == ["Freelance", "Salário"]

def test_category_search_does_not_duplicate_a_match_in_both_fields(session: Session):
    repo = SQLAlchemyCategoryRepository(session)
    repo.save(Category(name="Despesas gerais", type=TransactionType.EXPENSE))
    session.flush()

    page = repo.list_page(page=1, page_size=10, search="despesa")

    assert page.total == 1

def test_category_search_treats_wildcards_as_text(session: Session):
    repo = _seed_categories(session)

    assert repo.list_page(page=1, page_size=10, search="%").total == 0
    assert repo.list_page(page=1, page_size=10, search="_").total == 0

def test_category_pagination_works_over_the_search_results(session: Session):
    repo = _seed_categories(session)

    page = repo.list_page(page=2, page_size=1, search="receita")

    assert page.total == 2
    assert [c.name for c in page.items] == ["Salário"]
