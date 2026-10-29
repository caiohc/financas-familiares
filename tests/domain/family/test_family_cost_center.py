import pytest
from domain.shared.exceptions import DomainValidationError
import uuid
from domain.family.entities import FamilyCostCenter

def test_family_cost_center_creation():
    fam_id = uuid.uuid4()
    cc = FamilyCostCenter(family_id=fam_id, name="Núcleo Sogra")
    
    assert cc.family_id == fam_id
    assert cc.name == "Núcleo Sogra"
    assert cc.description is None
    assert isinstance(cc.id, uuid.UUID)

@pytest.mark.parametrize("blank_name", [None, "", "   "])
def test_family_cost_center_invalid_name(blank_name):
    with pytest.raises(DomainValidationError, match="Nome do centro de custo é obrigatório."):
        FamilyCostCenter(family_id=uuid.uuid4(), name=blank_name)

def test_family_cost_center_missing_family():
    with pytest.raises(DomainValidationError, match="O centro de custo deve pertencer a uma família."):
        FamilyCostCenter(family_id=None, name="Núcleo Sogra")

def test_family_cost_center_name_is_stripped_on_creation():
    cc = FamilyCostCenter(family_id=uuid.uuid4(), name="  Núcleo Sogra  ")
    assert cc.name == "Núcleo Sogra"

def test_family_cost_center_rename():
    cc = FamilyCostCenter(family_id=uuid.uuid4(), name="Núcleo Sogra")
    cc.rename("Casa de Praia")
    assert cc.name == "Casa de Praia"

def test_family_cost_center_rename_strips_name():
    cc = FamilyCostCenter(family_id=uuid.uuid4(), name="Núcleo Sogra")
    cc.rename("  Casa de Praia  ")
    assert cc.name == "Casa de Praia"

@pytest.mark.parametrize("blank_name", [None, "", "   "])
def test_family_cost_center_rename_to_blank_raises_and_keeps_current_name(blank_name):
    cc = FamilyCostCenter(family_id=uuid.uuid4(), name="Núcleo Sogra")

    with pytest.raises(DomainValidationError, match="Nome do centro de custo é obrigatório."):
        cc.rename(blank_name)

    assert cc.name == "Núcleo Sogra"

def test_family_cost_center_validation_errors_report_the_field():
    with pytest.raises(DomainValidationError) as name_error:
        FamilyCostCenter(family_id=uuid.uuid4(), name="   ")
    assert name_error.value.field == "name"

    with pytest.raises(DomainValidationError) as family_error:
        FamilyCostCenter(family_id=None, name="Núcleo Sogra")
    assert family_error.value.field == "family_id"
