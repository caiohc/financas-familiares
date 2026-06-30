from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import CreditCardBill

def test_credit_card_bill_creation_success():
    fam_id = uuid.uuid4()
    card_id = uuid.uuid4()
    from datetime import date
    due = date(2026, 4, 10)

    bill = CreditCardBill(
        family_id=fam_id,
        credit_card_id=card_id,
        reference_month="2026-04",
        due_date=due
    )

    assert isinstance(bill.id, uuid.UUID)
    assert bill.family_id == fam_id
    assert bill.credit_card_id == card_id
    assert bill.reference_month == "2026-04"
    assert bill.due_date == due
    assert bill.total_amount == Decimal('0.00')
    assert bill.is_closed is False

def test_credit_card_bill_validations():
    fam_id = uuid.uuid4()
    card_id = uuid.uuid4()
    from datetime import date
    due = date(2026, 4, 10)

    with pytest.raises(ValueError, match="associada a uma família"):
        CreditCardBill(family_id=None, credit_card_id=card_id, reference_month="2026-04", due_date=due)

    with pytest.raises(ValueError, match="associada a um contrato de cartão"):
        CreditCardBill(family_id=fam_id, credit_card_id=None, reference_month="2026-04", due_date=due)

    with pytest.raises(ValueError, match="formato YYYY-MM"):
        CreditCardBill(family_id=fam_id, credit_card_id=card_id, reference_month="04-2026", due_date=due)

    with pytest.raises(ValueError, match="data de vencimento.*informada"):
        CreditCardBill(family_id=fam_id, credit_card_id=card_id, reference_month="2026-04", due_date=None)
