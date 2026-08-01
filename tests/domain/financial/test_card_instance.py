import uuid
import pytest
from domain.financial.entities import CardInstance

def test_card_instance_creation_success():
    fam_id = uuid.uuid4()
    credit_card_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    instance = CardInstance(
        family_id=fam_id,
        credit_card_id=credit_card_id,
        holder_id=holder_id,
        nickname="Cartão Virtual para Ifood"
    )
    
    assert isinstance(instance.id, uuid.UUID)
    assert instance.family_id == fam_id
    assert instance.credit_card_id == credit_card_id
    assert instance.holder_id == holder_id
    assert instance.nickname == "Cartão Virtual para Ifood"

def test_card_instance_validations():
    fam_id = uuid.uuid4()
    card_id = uuid.uuid4()
    holder_id = uuid.uuid4()

    with pytest.raises(ValueError, match="associado a uma família"):
        CardInstance(family_id=None, credit_card_id=card_id, holder_id=holder_id, nickname="Físico")

    with pytest.raises(ValueError, match="associado a um contrato de cartão"):
        CardInstance(family_id=fam_id, credit_card_id=None, holder_id=holder_id, nickname="Físico")

    with pytest.raises(ValueError, match="deve ter um portador"):
        CardInstance(family_id=fam_id, credit_card_id=card_id, holder_id=None, nickname="Físico")
