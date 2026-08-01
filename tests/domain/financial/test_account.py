from dataclasses import dataclass
from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import Account, AccountType

@dataclass(kw_only=True)
class SimpleAccount(Account):

    def __post_init__(self):
        self.account_type = AccountType.ASSET
        super().__post_init__()

    def _validate_balance_invariants(self):
        pass
 
def test_account_creation_success():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    nickname = 'nickname'    

    acc = SimpleAccount(family_id=fam_id, holder_id=holder_id, nickname=nickname)
    
    assert isinstance(acc.id, uuid.UUID)
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == nickname
    assert acc.current_balance == Decimal('0.00')
    assert acc.account_type == AccountType.ASSET

def test_account_missing_family():

    with pytest.raises(ValueError, match="Toda conta.* deve estar vinculada a uma família.*"):
        SimpleAccount(family_id=None, holder_id=uuid.uuid4(), nickname="nickname")

def test_account_missing_holder():

    with pytest.raises(ValueError, match="Toda conta.* deve ter um titular.*"):
        SimpleAccount(family_id=uuid.uuid4(), holder_id=None, nickname="nickname")

def test_account_missing_nickname():
    
    with pytest.raises(ValueError, match="O apelido.* é obrigatório para uma conta.*"):
        SimpleAccount(family_id=uuid.uuid4(), holder_id=uuid.uuid4(), nickname=None)

    with pytest.raises(ValueError, match="O apelido.* é obrigatório para uma conta.*"):
        SimpleAccount(family_id=uuid.uuid4(), holder_id=uuid.uuid4(), nickname="")

    with pytest.raises(ValueError, match="O apelido.* é obrigatório para uma conta.*"):
        SimpleAccount(family_id=uuid.uuid4(), holder_id=uuid.uuid4(), nickname=" ")

