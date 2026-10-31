from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from domain.family.entities import Family, Member
from domain.financial.entities import Transaction, TransactionType, Category, BankAccount
from infrastructure.repositories.sqlalchemy_repositories import (
    SQLAlchemyFamilyRepository,
    SQLAlchemyMemberRepository,
    SQLAlchemyCategoryRepository,
    SQLAlchemyBankAccountRepository,
    SQLAlchemyTransactionRepository
)

def test_transaction_repository_save_and_get(session: Session):
    family_repo = SQLAlchemyFamilyRepository(session)
    member_repo = SQLAlchemyMemberRepository(session)
    cat_repo = SQLAlchemyCategoryRepository(session)
    acc_repo = SQLAlchemyBankAccountRepository(session)
    tx_repo = SQLAlchemyTransactionRepository(session)
    
    family = Family(name="Family TX")
    family_repo.save(family)
    
    member = Member(family_id=family.id, name="Tx Owner")
    member_repo.save(member)
    
    category = Category(name="Lazer", type=TransactionType.EXPENSE)
    cat_repo.save(category)
    
    account = BankAccount(family_id=family.id, holder_id=member.id, nickname="Conta Corrente", bank="BB")
    acc_repo.save(account)
    session.flush()
    
    tx = Transaction(
        family_id=family.id,
        category_id=category.id,
        type=TransactionType.EXPENSE,
        accrual_date=date(2026, 8, 1),
        due_date=date(2026, 8, 5),
        amount=Decimal("49.90"),
        description="Assinatura Streaming",
        is_forecast=False,
        account_id=account.id,
        installment_current=1,
        installment_total=12
    )
    tx_repo.save(tx)
    session.flush()
    
    fetched = tx_repo.get_by_id(tx.id)
    assert fetched is not None
    assert fetched.id == tx.id
    assert fetched.family_id == tx.family_id
    assert fetched.category_id == tx.category_id
    assert fetched.amount == tx.amount
    assert fetched.description == tx.description
    assert fetched.is_forecast == tx.is_forecast
    assert fetched.installment_current == tx.installment_current
    assert fetched.installment_total == tx.installment_total

def test_transaction_repository_list_by_period(session: Session):
    family_repo = SQLAlchemyFamilyRepository(session)
    member_repo = SQLAlchemyMemberRepository(session)
    cat_repo = SQLAlchemyCategoryRepository(session)
    acc_repo = SQLAlchemyBankAccountRepository(session)
    tx_repo = SQLAlchemyTransactionRepository(session)
    
    family = Family(name="Family TX List")
    family_repo.save(family)
    member = Member(family_id=family.id, name="Tx Owner 2")
    member_repo.save(member)
    cat = Category(name="Food", type=TransactionType.EXPENSE)
    cat_repo.save(cat)
    acc = BankAccount(family_id=family.id, holder_id=member.id, nickname="Conta 2", bank="BB")
    acc_repo.save(acc)
    session.flush()
    
    tx1 = Transaction(
        family_id=family.id, account_id=acc.id, category_id=cat.id,
        type=TransactionType.EXPENSE, accrual_date=date(2026, 8, 15), due_date=date(2026, 8, 15),
        amount=Decimal("100"), description="Almoço"
    )
    tx2 = Transaction(
        family_id=family.id, account_id=acc.id, category_id=cat.id,
        type=TransactionType.EXPENSE, accrual_date=date(2026, 9, 10), due_date=date(2026, 9, 10),
        amount=Decimal("200"), description="Jantar fora do mes"
    )
    tx_repo.save(tx1)
    tx_repo.save(tx2)
    session.flush()
    
    # Busca por família
    fetched = tx_repo.list_by_family(family.id)
    
    assert len(fetched) == 2
    
    for tx in [tx1, tx2]:
        f = next((t for t in fetched if t.id == tx.id), None)
        assert f is not None
        assert f.amount == tx.amount
