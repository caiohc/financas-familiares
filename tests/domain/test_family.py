from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import Family

def test_family_creation_success():

    family = Family(name="Silva")
    assert family.name == "Silva"
    assert family.current_balance == Decimal('0.00')
    assert isinstance(family.id, uuid.UUID)

def test_family_missing_name():

    with pytest.raises(ValueError, match="Nome da família.*é obrigatório"):
        Family(name=None)

    with pytest.raises(ValueError, match="Nome da família.*é obrigatório"):
        Family(name="")
        
    with pytest.raises(ValueError, match="Nome da família.*é obrigatório"):
        Family(name="   ")
