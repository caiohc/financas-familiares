from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import Wallet, AccountType

def test_wallet_creation_success():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = Wallet(family_id=fam_id, holder_id=holder_id, nickname="Carteira Físca")
    assert isinstance(acc.id, uuid.UUID)
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.account_type == AccountType.ASSET
    assert acc.current_balance == Decimal('0.00')
    
    
def test_wallet_prevents_negative_balance_on_creation():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="A conta de carteira em espécie.* não pode ter saldo negativo"):
        Wallet(family_id=fam_id, holder_id=holder_id, nickname="Carteira", current_balance=Decimal('-10.0'))
