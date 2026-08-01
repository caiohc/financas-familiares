import uuid
from decimal import Decimal
from datetime import date

from domain.family.entities import Family, Member
from domain.financial.entities import (
    BankAccount, Wallet, CreditCard, AccountsPayable,
    Category, Transaction, TransactionType, Transfer, CreditCardBill, MonthlyBalance
)

def setup_base_domain():
    fam = Family(name="Família Teste")
    mem = Member(family_id=fam.id, name="Caio H")
    
    bank = BankAccount(family_id=fam.id, holder_id=mem.id, nickname="Itaú", bank="Itaú")
    cc = CreditCard(family_id=fam.id, holder_id=mem.id, nickname="Nubank", brand="Mastercard", issuer="Nubank", due_day=10, limit=Decimal('5000'))
    ap = AccountsPayable(family_id=fam.id, holder_id=mem.id, nickname="Boletos")
    
    cat_income = Category(name="Salário", type=TransactionType.INCOME)
    cat_exp = Category(name="Despesa Geral", type=TransactionType.EXPENSE)
    cat_fees = Category(name="Juros e Multas", type=TransactionType.EXPENSE)
    
    return fam, mem, bank, cc, ap, cat_income, cat_exp, cat_fees

def test_scenario_1_setup_and_heterogeneous_income():
    fam, mem, bank, cc, ap, cat_income, cat_exp, cat_fees = setup_base_domain()
    
    # Renda 1 (Dia 5)
    tx_inc1 = Transaction(
        family_id=fam.id, account_id=bank.id, category_id=cat_income.id,
        type=TransactionType.INCOME, purchase_date=date(2026, 7, 5), due_date=date(2026, 7, 5),
        amount=Decimal('5000.00'), description="Salário Principal"
    )
    
    # Renda 2 (Dia 15)
    tx_inc2 = Transaction(
        family_id=fam.id, account_id=bank.id, category_id=cat_income.id,
        type=TransactionType.INCOME, purchase_date=date(2026, 7, 15), due_date=date(2026, 7, 15),
        amount=Decimal('1500.00'), description="Freela"
    )
    
    # Despesa à vista (Dia 10)
    tx_exp1 = Transaction(
        family_id=fam.id, account_id=bank.id, category_id=cat_exp.id,
        type=TransactionType.EXPENSE, purchase_date=date(2026, 7, 10), due_date=date(2026, 7, 10),
        amount=Decimal('800.00'), description="Supermercado"
    )
    
    # Matemática: 5000 + 1500 - 800 = 5700
    transactions = [tx_inc1, tx_inc2, tx_exp1]
    
    # Simula o Fechamento O(1) no fim de Julho
    mb = MonthlyBalance.create_from_history(
        account_id=bank.id, month="2026-07",
        previous_real_balance=Decimal('0.00'), previous_projected_balance=Decimal('0.00'),
        transactions=transactions
    )
    
    assert mb.real_balance == Decimal('5700.00')

def test_scenario_2_deferred_expense_and_clearing():
    fam, mem, bank, cc, ap, cat_income, cat_exp, cat_fees = setup_base_domain()
    
    # Boleto gerado (Fato gerador em Julho, Vencimento 10 de Agosto)
    tx_boleto = Transaction(
        family_id=fam.id, account_id=ap.id, category_id=cat_exp.id,
        type=TransactionType.EXPENSE, purchase_date=date(2026, 7, 1), due_date=date(2026, 8, 10),
        amount=Decimal('1000.00'), description="Condomínio"
    )
    
    # Fechamento de Julho: A dívida já consta no passivo!
    mb_jul_ap = MonthlyBalance.create_from_history(
        account_id=ap.id, month="2026-07",
        previous_real_balance=Decimal('0.00'), previous_projected_balance=Decimal('0.00'),
        transactions=[tx_boleto]
    )
    assert mb_jul_ap.real_balance == Decimal('-1000.00')
    
    # Em Agosto, o usuário paga atrasado no dia 15, com R$ 50 de multa.
    tx_multa = Transaction(
        family_id=fam.id, account_id=ap.id, category_id=cat_fees.id,
        type=TransactionType.EXPENSE, purchase_date=date(2026, 8, 15), due_date=date(2026, 8, 15),
        amount=Decimal('50.00'), description="Multa Condomínio"
    )
    
    # Transferência (O Pagamento Real)
    pagamento = Transfer(
        family_id=fam.id, source_account_id=bank.id, destination_account_id=ap.id,
        amount=Decimal('1050.00'), date=date(2026, 8, 15), description="Pagamento Condomínio"
    )
    out_tx, in_tx = pagamento.generate_transactions(category_id=cat_exp.id)
    
    # O "Pulo do Gato": Conciliação (Clearing)
    tx_boleto.settled_by_transfer_id = pagamento.id
    
    # Fechamento de Agosto do Passivo (AccountsPayable)
    # Considera o saldo do mês passado (-1000) + Multa (-50) + Pagamento (+1050)
    mb_aug_ap = MonthlyBalance.create_from_history(
        account_id=ap.id, month="2026-08",
        previous_real_balance=mb_jul_ap.real_balance, previous_projected_balance=mb_jul_ap.projected_balance,
        transactions=[tx_multa, in_tx]
    )
    
    assert tx_boleto.settled_by_transfer_id is not None
    assert mb_aug_ap.real_balance == Decimal('0.00')

def test_scenario_3_credit_card_installments():
    fam, mem, bank, cc, ap, cat_income, cat_exp, cat_fees = setup_base_domain()
    
    # Compra de R$ 1200 em 6x (R$ 200/mês) iniciada em Janeiro
    installments = []
    group_id = uuid.uuid4()
    for i in range(1, 7):
        installments.append(
            Transaction(
                family_id=fam.id, account_id=cc.id, category_id=cat_exp.id,
                type=TransactionType.EXPENSE, purchase_date=date(2026, 1, 10), due_date=date(2026, i, 10),
                amount=Decimal('200.00'), description=f"TV {i}/6",
                installment_current=i, installment_total=6, installment_group_id=group_id
            )
        )
    
    # O saldo do Cartão no balanço patrimonial imediato em Janeiro já retém a dívida completa!
    # Pois o passivo total compromete o limite e o patrimônio da família.
    mb_jan_cc = MonthlyBalance.create_from_history(
        account_id=cc.id, month="2026-01",
        previous_real_balance=Decimal('0.00'), previous_projected_balance=Decimal('0.00'),
        transactions=installments
    )
    assert mb_jan_cc.real_balance == Decimal('-1200.00')
    
    # Avançando 3 meses: Pagamos as faturas de Jan, Fev e Mar
    payments = []
    for i in range(1, 4):
        pagamento = Transfer(
            family_id=fam.id, source_account_id=bank.id, destination_account_id=cc.id,
            amount=Decimal('200.00'), date=date(2026, i, 10), description=f"Pagto Fatura {i}"
        )
        _, in_tx = pagamento.generate_transactions(category_id=cat_exp.id)
        payments.append(in_tx)
        
    # O Saldo do Cartão no final de Março: 
    # Dívida Inicial (-1200) + Pagamentos Realizados (+600) = Dívida Restante (-600)
    # Apenas as parcelas 4, 5 e 6 continuam machucando o balanço patrimonial
    mb_mar_cc = MonthlyBalance.create_from_history(
        account_id=cc.id, month="2026-03",
        previous_real_balance=Decimal('0.00'), previous_projected_balance=Decimal('0.00'),
        transactions=installments + payments
    )
    assert mb_mar_cc.real_balance == Decimal('-600.00')

def test_scenario_4_indebtedness_and_rollover():
    fam, mem, bank, cc, ap, cat_income, cat_exp, cat_fees = setup_base_domain()
    
    # --- MÊS 1 ---
    # Receitas: 3000. Despesas: 2000 (Débito) + 2000 (Cartão)
    tx_inc = Transaction(family_id=fam.id, account_id=bank.id, category_id=cat_income.id, type=TransactionType.INCOME, purchase_date=date(2026, 1, 5), due_date=date(2026, 1, 5), amount=Decimal('3000.00'), description="Salário")
    tx_exp_cash = Transaction(family_id=fam.id, account_id=bank.id, category_id=cat_exp.id, type=TransactionType.EXPENSE, purchase_date=date(2026, 1, 15), due_date=date(2026, 1, 15), amount=Decimal('2000.00'), description="Aluguel")
    tx_exp_cc = Transaction(family_id=fam.id, account_id=cc.id, category_id=cat_exp.id, type=TransactionType.EXPENSE, purchase_date=date(2026, 1, 20), due_date=date(2026, 2, 10), amount=Decimal('2000.00'), description="Móveis")
    
    mb_m1_bank = MonthlyBalance.create_from_history(account_id=bank.id, month="2026-01", previous_real_balance=Decimal('0.00'), previous_projected_balance=Decimal('0.00'), transactions=[tx_inc, tx_exp_cash])
    mb_m1_cc = MonthlyBalance.create_from_history(account_id=cc.id, month="2026-01", previous_real_balance=Decimal('0.00'), previous_projected_balance=Decimal('0.00'), transactions=[tx_exp_cc])
    
    assert mb_m1_bank.real_balance == Decimal('1000.00')
    assert mb_m1_cc.real_balance == Decimal('-2000.00')
    patrimony_m1 = mb_m1_bank.real_balance + mb_m1_cc.real_balance
    assert patrimony_m1 == Decimal('-1000.00') # Terminou o mês mais pobre do que começou
    
    # --- MÊS 2 ---
    # Receitas: 3000. Fatura: 2000. Paga apenas 1000 (Rolagem). Juros: 100. Nova compra CC: 500.
    tx_inc2 = Transaction(family_id=fam.id, account_id=bank.id, category_id=cat_income.id, type=TransactionType.INCOME, purchase_date=date(2026, 2, 5), due_date=date(2026, 2, 5), amount=Decimal('3000.00'), description="Salário")
    
    pagamento_parcial = Transfer(family_id=fam.id, source_account_id=bank.id, destination_account_id=cc.id, amount=Decimal('1000.00'), date=date(2026, 2, 10), description="Pagto Parcial Fatura")
    out_tx, in_tx = pagamento_parcial.generate_transactions(category_id=cat_exp.id)
    
    tx_fees = Transaction(family_id=fam.id, account_id=cc.id, category_id=cat_fees.id, type=TransactionType.EXPENSE, purchase_date=date(2026, 2, 15), due_date=date(2026, 3, 10), amount=Decimal('100.00'), description="Juros Rolagem")
    tx_new_cc = Transaction(family_id=fam.id, account_id=cc.id, category_id=cat_exp.id, type=TransactionType.EXPENSE, purchase_date=date(2026, 2, 20), due_date=date(2026, 3, 10), amount=Decimal('500.00'), description="Roupas")
    
    mb_m2_bank = MonthlyBalance.create_from_history(account_id=bank.id, month="2026-02", previous_real_balance=mb_m1_bank.real_balance, previous_projected_balance=mb_m1_bank.projected_balance, transactions=[tx_inc2, out_tx])
    mb_m2_cc = MonthlyBalance.create_from_history(account_id=cc.id, month="2026-02", previous_real_balance=mb_m1_cc.real_balance, previous_projected_balance=mb_m1_cc.projected_balance, transactions=[in_tx, tx_fees, tx_new_cc])
    
    # Banco: 1000 (Prev) + 3000 (Renda) - 1000 (Pagto) = 3000
    assert mb_m2_bank.real_balance == Decimal('3000.00')
    
    # CC: -2000 (Prev) + 1000 (Pagto IN) - 100 (Juros) - 500 (Roupas) = -1600
    assert mb_m2_cc.real_balance == Decimal('-1600.00')
    
    # Patrimônio: 3000 - 1600 = 1400.
    patrimony_m2 = mb_m2_bank.real_balance + mb_m2_cc.real_balance
    assert patrimony_m2 == Decimal('1400.00')
