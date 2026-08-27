from decimal import Decimal
from sqlalchemy.orm import Session
from domain.family.entities import Family, Member
from domain.financial.entities import CreditCard, AccountType, BankAccount
from infrastructure.repositories.sqlalchemy_repositories import (
    SQLAlchemyFamilyRepository,
    SQLAlchemyMemberRepository,
    SQLAlchemyCreditCardRepository,
    SQLAlchemyBankAccountRepository
)

def test_credit_card_repository_save_and_get(session: Session):
    family_repo = SQLAlchemyFamilyRepository(session)
    member_repo = SQLAlchemyMemberRepository(session)
    bank_repo = SQLAlchemyBankAccountRepository(session)
    card_repo = SQLAlchemyCreditCardRepository(session)
    
    family = Family(name="Family CC")
    family_repo.save(family)
    
    member = Member(family_id=family.id, name="Card Holder")
    member_repo.save(member)
    
    bank_account = BankAccount(
        family_id=family.id, holder_id=member.id, nickname="Conta Vinculada", bank="Itaú"
    )
    bank_repo.save(bank_account)
    session.flush()
    
    card = CreditCard(
        family_id=family.id,
        holder_id=member.id,
        nickname="Cartão Black",
        brand="Mastercard",
        issuer="Itaú",
        tier="Black",
        limit=Decimal("20000.00"),
        due_day=5,
        bank_account_id=bank_account.id
    )
    card_repo.save(card)
    session.flush()
    
    fetched = card_repo.get_by_id(card.id)
    assert fetched is not None
    assert fetched.id == card.id
    assert fetched.family_id == card.family_id
    assert fetched.nickname == card.nickname
    assert fetched.brand == card.brand
    assert fetched.tier == card.tier
    assert fetched.limit == card.limit
    assert fetched.due_day == card.due_day
    assert fetched.bank_account_id == card.bank_account_id
    assert fetched.account_type == AccountType.LIABILITY
