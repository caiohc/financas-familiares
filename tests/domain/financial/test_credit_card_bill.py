from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import CreditCardBill, Transaction, TransactionType

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
    assert bill.previous_balance == Decimal('0.00')
    assert bill.payments_received == Decimal('0.00')
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

def test_credit_card_bill_calculate_total():
    fam_id = uuid.uuid4()
    card_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    from datetime import date
    
    # Saldo da fatura anterior (R$ 1.000) e Pagamento feito (R$ 400)
    # Sobrou uma dívida rolada de R$ 600
    prev_balance = Decimal('1000.00')
    payments = Decimal('400.00')
    
    # Novas despesas na fatura atual
    tx1 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.EXPENSE, purchase_date=date(2026, 5, 10), due_date=date(2026, 6, 10), 
        amount=Decimal('100.00'), description="Mercado"
    )
    
    tx2 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.EXPENSE, purchase_date=date(2026, 5, 15), due_date=date(2026, 6, 10), 
        amount=Decimal('50.00'), description="Uber"
    )
    
    # Juros adicionados pelo banco (também é uma despesa)
    tx3 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.EXPENSE, purchase_date=date(2026, 5, 20), due_date=date(2026, 6, 10), 
        amount=Decimal('15.00'), description="Juros de mora"
    )

    # Estorno de compra (Entra como receita na fatura)
    tx4 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.INCOME, purchase_date=date(2026, 5, 22), due_date=date(2026, 6, 10), 
        amount=Decimal('20.00'), description="Estorno Mercado Livre"
    )
    
    transactions = [tx1, tx2, tx3, tx4]
    
    bill = CreditCardBill.calculate_total(
        family_id=fam_id,
        credit_card_id=card_id,
        month="2026-05",
        due_date=date(2026, 6, 10),
        previous_balance=prev_balance,
        payments_received=payments,
        transactions=transactions
    )
    
    # Matemática: (1000 - 400) + 100 + 50 + 15 - 20 = 745
    assert bill.previous_balance == Decimal('1000.00')
    assert bill.payments_received == Decimal('400.00')
    assert bill.total_amount == Decimal('745.00')
    assert bill.reference_month == "2026-05"
    assert bill.due_date == date(2026, 6, 10)
