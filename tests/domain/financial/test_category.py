import uuid
import pytest
from domain.financial.entities import Category, TransactionType
from domain.shared.exceptions import DomainValidationError

def test_category_creation_success():
    cat = Category(name="Alimentação", type=TransactionType.EXPENSE)
    assert isinstance(cat.id, uuid.UUID)
    assert cat.name == "Alimentação"
    assert cat.type == TransactionType.EXPENSE

@pytest.mark.parametrize("blank_name", [None, "", "   "])
def test_category_missing_name(blank_name):
    with pytest.raises(DomainValidationError, match="Nome da categoria.* é obrigatório"):
        Category(name=blank_name, type=TransactionType.EXPENSE)

def test_category_missing_type():
    with pytest.raises(DomainValidationError, match="Tipo da categoria.* é obrigatório"):
        Category(name="Lazer", type=None)

def test_category_validation_errors_report_the_field():
    with pytest.raises(DomainValidationError) as name_error:
        Category(name="   ", type=TransactionType.EXPENSE)
    assert name_error.value.field == "name"

    with pytest.raises(DomainValidationError) as type_error:
        Category(name="Lazer", type=None)
    assert type_error.value.field == "type"

def test_category_name_is_stripped_on_creation():
    assert Category(name="  Lazer  ", type=TransactionType.EXPENSE).name == "Lazer"

def test_category_rename():
    cat = Category(name="Lazer", type=TransactionType.EXPENSE)
    cat.rename("  Diversão  ")
    assert cat.name == "Diversão"

@pytest.mark.parametrize("blank_name", [None, "", "   "])
def test_category_rename_to_blank_raises_and_keeps_current_name(blank_name):
    cat = Category(name="Lazer", type=TransactionType.EXPENSE)

    with pytest.raises(DomainValidationError, match="Nome da categoria.* é obrigatório"):
        cat.rename(blank_name)

    assert cat.name == "Lazer"

def test_category_change_type():
    cat = Category(name="Vendas", type=TransactionType.EXPENSE)
    cat.change_type(TransactionType.INCOME)
    assert cat.type == TransactionType.INCOME

def test_category_change_type_to_none_raises_and_keeps_current_type():
    cat = Category(name="Vendas", type=TransactionType.INCOME)

    with pytest.raises(DomainValidationError, match="Tipo da categoria.* é obrigatório"):
        cat.change_type(None)

    assert cat.type == TransactionType.INCOME
