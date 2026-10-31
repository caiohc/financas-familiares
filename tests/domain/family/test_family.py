from decimal import Decimal
import uuid
import pytest
from domain.shared.exceptions import DomainValidationError
from domain.family.entities import Family

def test_family_creation_success():

    family = Family(name="Silva")
    assert family.name == "Silva"
    assert family.current_balance == Decimal('0.00')
    assert isinstance(family.id, uuid.UUID)

@pytest.mark.parametrize("blank_name", [None, "", "   "])
def test_family_missing_name(blank_name):
    with pytest.raises(DomainValidationError, match="Nome da família.* é obrigatório"):
        Family(name=blank_name)

def test_family_name_is_stripped_on_creation():
    family = Family(name="  Silva  ")
    assert family.name == "Silva"

def test_family_rename():
    family = Family(name="Silva")
    family.rename("Souza")
    assert family.name == "Souza"

def test_family_rename_strips_name():
    family = Family(name="Silva")
    family.rename("  Souza  ")
    assert family.name == "Souza"

@pytest.mark.parametrize("blank_name", [None, "", "   "])
def test_family_rename_to_blank_raises_and_keeps_current_name(blank_name):
    family = Family(name="Silva")

    with pytest.raises(DomainValidationError, match="Nome da família.* é obrigatório"):
        family.rename(blank_name)

    assert family.name == "Silva"

def test_family_invalid_name_reports_the_field():
    with pytest.raises(DomainValidationError) as exc_info:
        Family(name="   ")
    assert exc_info.value.field == "name"
