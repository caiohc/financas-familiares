import uuid
import pytest
from domain.financial.entities import AccountsPayable, AccountType

def test_accounts_payable_creation_success():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = AccountsPayable(family_id=fam_id, holder_id=holder_id, nickname="Boletos Gerais")
    assert isinstance(acc.id, uuid.UUID)
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == "Boletos Gerais"
    assert acc.account_type == AccountType.LIABILITY
