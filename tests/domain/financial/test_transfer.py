from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import Transfer, TransactionType

def test_transfer_creation_success():
    fam_id = uuid.uuid4()
    src_id = uuid.uuid4()
    dst_id = uuid.uuid4()
    from datetime import date
    
    transfer = Transfer(
        family_id=fam_id,
        source_account_id=src_id,
        destination_account_id=dst_id,
        amount=Decimal('150.50'),
        date=date.today(),
        description="Mesada"
    )
    
    assert isinstance(transfer.id, uuid.UUID)
    assert transfer.amount == Decimal('150.50')
    assert transfer.description == "Mesada"

def test_transfer_invalid_amount():
    fam_id = uuid.uuid4()
    src_id = uuid.uuid4()
    dst_id = uuid.uuid4()
    from datetime import date
    
    with pytest.raises(ValueError, match="O valor da transferência.*deve ser maior que zero"):
        Transfer(
            family_id=fam_id, source_account_id=src_id, destination_account_id=dst_id,
            amount=Decimal('0.0'), date=date.today(), description="Transferência"
        )
        
    with pytest.raises(ValueError, match="O valor da transferência.*deve ser maior que zero"):
        Transfer(
            family_id=fam_id, source_account_id=src_id, destination_account_id=dst_id,
            amount=Decimal('-50.0'), date=date.today(), description="Transferência"
        )

def test_transfer_same_account_error():
    fam_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    from datetime import date
    
    with pytest.raises(ValueError, match="A conta de origem e destino.*não podem ser a mesma"):
        Transfer(
            family_id=fam_id, source_account_id=acc_id, destination_account_id=acc_id,
            amount=Decimal('100.0'), date=date.today(), description="Transferência"
        )

def test_transfer_generate_transactions():
    fam_id = uuid.uuid4()
    src_id = uuid.uuid4()
    dst_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    from datetime import date
    
    transfer = Transfer(
        family_id=fam_id,
        source_account_id=src_id,
        destination_account_id=dst_id,
        amount=Decimal('200.0'),
        date=date.today(),
        description="Pagamento fatura"
    )
    
    out_tx, in_tx = transfer.generate_transactions(category_id=cat_id)
    
    assert out_tx.type == TransactionType.TRANSFER_OUT
    assert out_tx.account_id == src_id
    assert out_tx.amount == Decimal('200.0')
    assert out_tx.transfer_id == transfer.id
    assert out_tx.category_id == cat_id
    assert out_tx.is_forecast is False
    
    assert in_tx.type == TransactionType.TRANSFER_IN
    assert in_tx.account_id == dst_id
    assert in_tx.amount == Decimal('200.0')
    assert in_tx.transfer_id == transfer.id
    assert in_tx.category_id == cat_id
    assert in_tx.is_forecast is False
