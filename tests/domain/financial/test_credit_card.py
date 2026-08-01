from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import CreditCard, AccountType

def test_credit_card_creation_success():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    bank_account_id=uuid.uuid4()

    acc = CreditCard(
        family_id=fam_id, holder_id=holder_id, nickname="VISA Gold do Pedro", 
        brand="VISA", limit=5000.0, due_day=10, issuer="Nubank", tier="Gold",
        bank_account_id=bank_account_id
    )

    assert isinstance(acc.id, uuid.UUID)
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == "VISA Gold do Pedro"
    assert acc.brand == "VISA"
    assert acc.limit == Decimal('5000.00')
    assert acc.due_day == 10
    assert acc.issuer == "Nubank"
    assert acc.tier == "Gold"
    assert acc.bank_account_id == bank_account_id
    assert acc.account_type == AccountType.LIABILITY

    acc = CreditCard(
        family_id=fam_id, holder_id=holder_id, nickname="VISA Gold do Pedro", 
        brand="VISA", limit=5000.0, due_day=10, tier="Gold",
        bank_account_id=bank_account_id
    )

    assert isinstance(acc.id, uuid.UUID)
    assert acc.issuer == None
    assert acc.account_type == AccountType.LIABILITY

    acc = CreditCard(
        family_id=fam_id, holder_id=holder_id, nickname="VISA Gold do Pedro", 
        brand="VISA", limit=5000.0, due_day=10, tier="Gold", issuer="Nubank"
    )

    assert isinstance(acc.id, uuid.UUID)
    assert acc.issuer == 'Nubank'
    assert acc.bank_account_id == None
    assert acc.account_type == AccountType.LIABILITY

def test_credit_card_missing_brand():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="A bandeira.* do cartão de crédito.* deve ser informada"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="", limit=5000.0, due_day=10, issuer="Nubank"
        )

    with pytest.raises(ValueError, match="A bandeira.* do cartão de crédito.* deve ser informada"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand=None, limit=5000.0, due_day=10, issuer="Nubank"
        )

    with pytest.raises(ValueError, match="A bandeira.* do cartão de crédito.* deve ser informada"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="  ", limit=5000.0, due_day=10, issuer="Nubank"
        )

def test_credit_card_missing_bank_and_issuer():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="Um cartão de crédito.*deve ter uma conta bancária.* vinculada ou um emissor.*"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="Mastercard", limit=5000.0, due_day=10, issuer=None, bank_account_id=None
        )

    with pytest.raises(ValueError, match="Um cartão de crédito.*deve ter uma conta bancária.* vinculada ou um emissor.*"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="Mastercard", limit=5000.0, due_day=10, issuer="", bank_account_id=None
        )

    with pytest.raises(ValueError, match="Um cartão de crédito.*deve ter uma conta bancária.* vinculada ou um emissor.*"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="Mastercard", limit=5000.0, due_day=10, issuer="  ", bank_account_id=None
        )

def test_credit_card_invalid_due_day():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="O dia de vencimento.*entre 1 e 31"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="Mastercard", limit=5000.0, due_day=0, issuer="Nubank"
        )

    with pytest.raises(ValueError, match="O dia de vencimento.*entre 1 e 31"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="Mastercard", limit=5000.0, due_day=32, issuer="Nubank"
        )
