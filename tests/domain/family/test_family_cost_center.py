import pytest
import uuid
from domain.family.entities import FamilyCostCenter

def test_family_cost_center_creation():
    fam_id = uuid.uuid4()
    cc = FamilyCostCenter(family_id=fam_id, name="Núcleo Sogra")
    
    assert cc.family_id == fam_id
    assert cc.name == "Núcleo Sogra"
    assert cc.description == ""
    assert isinstance(cc.id, uuid.UUID)

def test_family_cost_center_invalid_name():
    with pytest.raises(ValueError, match="Nome do centro de custo é obrigatório."):
        FamilyCostCenter(family_id=uuid.uuid4(), name="")
        
    with pytest.raises(ValueError, match="Nome do centro de custo é obrigatório."):
        FamilyCostCenter(family_id=uuid.uuid4(), name="   ")

def test_family_cost_center_missing_family():
    with pytest.raises(ValueError, match="O centro de custo deve pertencer a uma família."):
        FamilyCostCenter(family_id=None, name="Núcleo Sogra")
