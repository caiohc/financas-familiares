from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import BankAccount, AccountType

def test_bank_account_creation_success():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = BankAccount(family_id=fam_id, holder_id=holder_id, nickname="Minha Conta", bank="Nubank", 
        agency='001', account_number='123456-7')
    assert isinstance(acc.id, uuid.UUID)
    assert acc.account_type == AccountType.ASSET
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == "Minha Conta"
    assert acc.bank == "Nubank"
    assert acc.current_balance == Decimal('0.00')
    assert acc.agency == "001"
    assert acc.account_number == "123456-7"


    acc = BankAccount(family_id=fam_id, holder_id=holder_id, nickname="Minha Conta", bank="Nubank")
    assert isinstance(acc.id, uuid.UUID)
    assert acc.account_type == AccountType.ASSET
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == "Minha Conta"
    assert acc.bank == "Nubank"
    assert acc.current_balance == Decimal('0.00')


def test_bank_account_missing_bank():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="O nome do banco.*é obrigatório para uma conta bancária.*"):
        BankAccount(family_id=fam_id, holder_id=holder_id, nickname="X", bank=None)

    with pytest.raises(ValueError, match="O nome do banco.*é obrigatório para uma conta bancária.*"):
        BankAccount(family_id=fam_id, holder_id=holder_id, nickname="X", bank="")    
    
    with pytest.raises(ValueError, match="O nome do banco.*é obrigatório para uma conta bancária.*"):
        BankAccount(family_id=fam_id, holder_id=holder_id, nickname="X", bank="   ")
