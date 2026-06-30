from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import MonthlyBalance, Transaction, TransactionType

def test_monthly_balance_validations():
    acc_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="O registro de saldo mensal deve estar associado a uma conta."):
        MonthlyBalance(account_id=None, reference_month="2026-05", real_balance=Decimal('100.0'), projected_balance=Decimal('100.0'))
        
    with pytest.raises(ValueError, match="O mês de referência deve ser informado no formato YYYY-MM."):
        MonthlyBalance(account_id=acc_id, reference_month="05-2026", real_balance=Decimal('100.0'), projected_balance=Decimal('100.0'))
        
    with pytest.raises(ValueError, match="O registro de saldo mensal deve ter os valores real e projetado."):
        MonthlyBalance(account_id=acc_id, reference_month="2026-05", real_balance=None, projected_balance=Decimal('100.0'))

def test_monthly_balance_create_from_history():
    acc_id = uuid.uuid4()
    fam_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    from datetime import date
    
    # Saldo inicial
    prev_real = Decimal('1000.00')
    prev_proj = Decimal('1000.00')
    
    # + 500 (Receita)
    tx1 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.INCOME, date=date(2026, 5, 10), 
        amount=Decimal('500.00'), description="Salário"
    )
    
    # - 200 (Despesa)
    tx2 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.EXPENSE, date=date(2026, 5, 12), 
        amount=Decimal('200.00'), description="Luz"
    )
    
    # - 100 (Transferência saindo)
    tx3 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.TRANSFER_OUT, date=date(2026, 5, 15), 
        amount=Decimal('100.00'), description="Pix para Investimento"
    )
    
    # + 300 (Transferência entrando)
    tx4 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.TRANSFER_IN, date=date(2026, 5, 20), 
        amount=Decimal('300.00'), description="Pix recebido"
    )
    
    # - 150 (Despesa prevista)
    tx5 = Transaction(
        family_id=fam_id, account_id=acc_id, category_id=cat_id, 
        type=TransactionType.EXPENSE, date=date(2026, 5, 25), 
        amount=Decimal('150.00'), description="Internet", is_forecast=True
    )
    
    transactions = [tx1, tx2, tx3, tx4, tx5]
    
    snapshot = MonthlyBalance.create_from_history(
        account_id=acc_id,
        month="2026-05",
        previous_real_balance=prev_real,
        previous_projected_balance=prev_proj,
        transactions=transactions
    )
    
    # Matemática real (ignora previsões): 1000 + 500 - 200 - 100 + 300 = 1500
    # Matemática projetada (inclui previsões): 1000 + 500 - 200 - 100 + 300 - 150 = 1350
    assert snapshot.account_id == acc_id
    assert snapshot.reference_month == "2026-05"
    assert snapshot.real_balance == Decimal('1500.00')
    assert snapshot.projected_balance == Decimal('1350.00')
    assert isinstance(snapshot.id, uuid.UUID)
