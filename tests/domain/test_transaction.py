from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import Transaction, TransactionType

def test_transaction_creation_success():
    fam_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    from datetime import date
    
    tx = Transaction(
        family_id=fam_id,
        category_id=cat_id,
        account_id=uuid.uuid4(),
        type=TransactionType.EXPENSE,
        date=date.today(),
        amount=Decimal('50.00'),
        description="Supermercado"
    )

    assert tx.id is not None
    assert tx.account_id is not None
    assert tx.family_id == fam_id
    assert tx.category_id == cat_id
    assert tx.type == TransactionType.EXPENSE
    assert tx.date == date.today()
    assert tx.amount == Decimal('50.00')
    assert tx.description == "Supermercado"
    assert tx.is_forecast is False

def test_transaction_validations():
    fam_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    from datetime import date
    dt = date.today()

    with pytest.raises(ValueError, match="pertencer a uma família"):
        Transaction(family_id=None, category_id=cat_id, account_id=acc_id, type=TransactionType.EXPENSE, date=dt, amount=Decimal('10'), description="D")

    with pytest.raises(ValueError, match="ter uma categoria"):
        Transaction(family_id=fam_id, category_id=None, account_id=acc_id, type=TransactionType.EXPENSE, date=dt, amount=Decimal('10'), description="D")

    with pytest.raises(ValueError, match="ter um tipo"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=acc_id, type=None, date=dt, amount=Decimal('10'), description="D")

    with pytest.raises(ValueError, match="ter uma data"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=acc_id, type=TransactionType.EXPENSE, date=None, amount=Decimal('10'), description="D")

    with pytest.raises(ValueError, match="ter um valor"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=acc_id, type=TransactionType.EXPENSE, date=dt, amount=None, description="D")

    with pytest.raises(ValueError, match="ter uma descrição"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=acc_id, type=TransactionType.EXPENSE, date=dt, amount=Decimal('10'), description="")

    with pytest.raises(ValueError, match="informar se é uma previsão"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=acc_id, type=TransactionType.EXPENSE, date=dt, amount=Decimal('10'), description="D", is_forecast="False")

    with pytest.raises(ValueError, match="associada a uma conta"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=None, type=TransactionType.EXPENSE, date=dt, amount=Decimal('10'), description="D")
