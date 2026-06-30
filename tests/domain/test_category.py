import uuid
import pytest
from domain.financial.entities import Category, TransactionType

def test_category_creation_success():
    cat = Category(name="Alimentação", type=TransactionType.EXPENSE)
    assert isinstance(cat.id, uuid.UUID)
    assert cat.name == "Alimentação"
    assert cat.type == TransactionType.EXPENSE

def test_category_missing_name():
    with pytest.raises(ValueError, match="Nome da categoria.*é obrigatório"):
        Category(name=None, type=TransactionType.EXPENSE)
    
    with pytest.raises(ValueError, match="Nome da categoria.*é obrigatório"):
        Category(name="   ", type=TransactionType.EXPENSE)

def test_category_missing_type():
    with pytest.raises(ValueError, match="Tipo da categoria.*é obrigatório"):
        Category(name="Lazer", type=None)
