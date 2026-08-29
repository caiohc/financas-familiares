from decimal import Decimal
from sqlalchemy.orm import Session
from domain.family.entities import Family, Member
from domain.financial.entities import BankAccount, AccountType
from infrastructure.repositories.sqlalchemy_repositories import (
    SQLAlchemyFamilyRepository,
    SQLAlchemyMemberRepository,
    SQLAlchemyBankAccountRepository
)

def test_bank_account_repository_save_and_get(session: Session):
    family_repo = SQLAlchemyFamilyRepository(session)
    member_repo = SQLAlchemyMemberRepository(session)
    account_repo = SQLAlchemyBankAccountRepository(session)
    
    family = Family(name="Test Family")
    family_repo.save(family)
    
    member = Member(family_id=family.id, name="Titular")
    member_repo.save(member)
    session.flush()
    
    account = BankAccount(
        family_id=family.id,
        holder_id=member.id,
        nickname="Conta Principal",
        current_balance=Decimal("250.75"),
        bank="Nubank",
        agency="0001",
        account_number="123456-7"
    )
    account_repo.save(account)
    session.flush()
    
    fetched = account_repo.get_by_id(account.id)
    assert fetched is not None
    assert fetched.id == account.id
    assert fetched.family_id == account.family_id
    assert fetched.holder_id == account.holder_id
    assert fetched.nickname == account.nickname
    assert fetched.current_balance == account.current_balance
    assert fetched.bank == account.bank
    assert fetched.agency == account.agency
    assert fetched.account_number == account.account_number
    assert fetched.account_type == AccountType.ASSET

def test_bank_account_repository_list_by_family(session: Session):
    family_repo = SQLAlchemyFamilyRepository(session)
    member_repo = SQLAlchemyMemberRepository(session)
    account_repo = SQLAlchemyBankAccountRepository(session)
    
    family = Family(name="List Accounts Family")
    family_repo.save(family)
    
    member = Member(family_id=family.id, name="Titular 2")
    member_repo.save(member)
    
    accounts = []
    for i in range(2):
        acc = BankAccount(
            family_id=family.id,
            holder_id=member.id,
            nickname=f"Conta {i}",
            bank="Banco"
        )
        accounts.append(acc)
        account_repo.save(acc)
    session.flush()
    
    fetched_accounts = account_repo.list_by_family(family.id)
    assert len(fetched_accounts) == len(accounts)
    
    for acc in accounts:
        fetched = next((a for a in fetched_accounts if a.id == acc.id), None)
        assert fetched is not None
        assert fetched.nickname == acc.nickname
