import uuid
import pytest
from domain.financial.entities import Tab, AccountType

def test_tab_creation_success():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = Tab(family_id=fam_id, holder_id=holder_id, nickname="Padaria do Zé")
    assert isinstance(acc.id, uuid.UUID)
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == "Padaria do Zé"
    assert acc.account_type == AccountType.LIABILITY
