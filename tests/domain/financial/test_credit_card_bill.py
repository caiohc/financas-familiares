from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import CreditCardBill, Transaction, TransactionType
from datetime import date

def test_credit_card_bill_creation_success():
    fam_id = uuid.uuid4()
    card_id = uuid.uuid4()
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
    assert bill.settled_by_transfer_ids == []
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
    
    # Saldo da fatura anterior (R$ 1.000) e Pagamento feito (R$ 400)
    # Sobrou uma dívida rolada de R$ 600
    prev_balance = Decimal('1000.00')
    payments = Decimal('400.00')
    
    # Novas despesas na fatura atual
    tx1 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.EXPENSE, accrual_date=date(2026, 5, 10), due_date=date(2026, 6, 10), 
        amount=Decimal('100.00'), description="Mercado"
    )
    
    tx2 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.EXPENSE, accrual_date=date(2026, 5, 15), due_date=date(2026, 6, 10), 
        amount=Decimal('50.00'), description="Uber"
    )
    
    # Juros adicionados pelo banco (também é uma despesa) apontando para a fatura do mês anterior (hipotético)
    old_bill_id = uuid.uuid4()
    tx3 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.EXPENSE, accrual_date=date(2026, 5, 20), due_date=date(2026, 6, 10), 
        amount=Decimal('15.00'), description="Juros de mora",
        originating_bill_id=old_bill_id
    )

    # Estorno de compra (Entra como receita na fatura)
    tx4 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.INCOME, accrual_date=date(2026, 5, 22), due_date=date(2026, 6, 10), 
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
    assert tx3.originating_bill_id == old_bill_id
    assert bill.reference_month == "2026-05"
    assert bill.due_date == date(2026, 6, 10)

def test_credit_card_bill_partial_payment_and_rollover_scenario():
    """
    Testa o ciclo de vida completo onde uma Fatura (Mês 1) é parcialmente paga.
    O saldo restante é rolado para a Fatura (Mês 2), e encargos são gerados com
    originating_bill_id apontando para a fatura do Mês 1.
    """
    fam_id = uuid.uuid4()
    card_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    cat_exp = uuid.uuid4()
    cat_fee = uuid.uuid4()

    # --- MÊS 1 ---
    # Compras no Mês 1 (Total R$ 2000)
    tx1_m1 = Transaction(family_id=fam_id, account_id=acc_id, category_id=cat_exp, type=TransactionType.EXPENSE, accrual_date=date(2026, 1, 10), due_date=date(2026, 2, 10), amount=Decimal('1500.00'), description="TV")
    tx2_m1 = Transaction(family_id=fam_id, account_id=acc_id, category_id=cat_exp, type=TransactionType.EXPENSE, accrual_date=date(2026, 1, 15), due_date=date(2026, 2, 10), amount=Decimal('500.00'), description="Supermercado")
    
    bill_m1 = CreditCardBill.calculate_total(
        family_id=fam_id, credit_card_id=card_id, month="2026-01", due_date=date(2026, 2, 10),
        previous_balance=Decimal('0.00'), payments_received=Decimal('0.00'), transactions=[tx1_m1, tx2_m1]
    )
    assert bill_m1.total_amount == Decimal('2000.00')

    # Pagamento parcial do Mês 1 (R$ 800)
    transfer_id_pgto = uuid.uuid4()
    bill_m1.settled_by_transfer_ids.append(transfer_id_pgto)
    pgto_m1 = Decimal('800.00')
    
    # O valor rolado para o mês 2 será 2000 - 800 = 1200
    rolled_debt = bill_m1.total_amount - pgto_m1

    # --- MÊS 2 ---
    # O banco cobra R$ 100 de Juros pelo atraso. A transação aponta para bill_m1.id
    tx_fee_m2 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_fee, type=TransactionType.EXPENSE, 
        accrual_date=date(2026, 2, 11), due_date=date(2026, 3, 10), amount=Decimal('100.00'), 
        description="Juros do Mês 1", originating_bill_id=bill_m1.id
    )

    # Novas compras no Mês 2 (Total R$ 300)
    tx_new_m2 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_exp, type=TransactionType.EXPENSE, 
        accrual_date=date(2026, 2, 20), due_date=date(2026, 3, 10), amount=Decimal('300.00'), 
        description="Roupas"
    )

    bill_m2 = CreditCardBill.calculate_total(
        family_id=fam_id, credit_card_id=card_id, month="2026-02", due_date=date(2026, 3, 10),
        previous_balance=rolled_debt, payments_received=Decimal('0.00'), transactions=[tx_fee_m2, tx_new_m2]
    )

    # Matemática Mês 2: 1200 (rolado) + 100 (juros) + 300 (roupas) = 1600
    assert bill_m2.previous_balance == Decimal('1200.00')
    assert bill_m2.total_amount == Decimal('1600.00')
    
    # Validação de integridade semântica
    assert tx_fee_m2.originating_bill_id == bill_m1.id
    assert transfer_id_pgto in bill_m1.settled_by_transfer_ids
