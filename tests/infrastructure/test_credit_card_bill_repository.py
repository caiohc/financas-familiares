from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from domain.family.entities import Family, Member
from domain.financial.entities import CreditCard, CreditCardBill
from infrastructure.repositories.sqlalchemy_repositories import (
    SQLAlchemyFamilyRepository,
    SQLAlchemyMemberRepository,
    SQLAlchemyCreditCardRepository,
    SQLAlchemyCreditCardBillRepository
)

def test_credit_card_bill_repository_save_and_get(session: Session):
    family_repo = SQLAlchemyFamilyRepository(session)
    member_repo = SQLAlchemyMemberRepository(session)
    card_repo = SQLAlchemyCreditCardRepository(session)
    bill_repo = SQLAlchemyCreditCardBillRepository(session)
    
    family = Family(name="Family Bill")
    family_repo.save(family)
    
    member = Member(family_id=family.id, name="Bill Holder")
    member_repo.save(member)
    
    card = CreditCard(
        family_id=family.id,
        holder_id=member.id,
        nickname="Cartão Bill",
        brand="Visa",
        issuer="Bradesco"
    )
    card_repo.save(card)
    session.flush()
    
    bill = CreditCardBill(
        family_id=family.id,
        credit_card_id=card.id,
        reference_month="2026-08",
        due_date=date(2026, 8, 10),
        previous_balance=Decimal("150.00"),
        total_amount=Decimal("1150.00"),
        is_closed=False
    )
    bill_repo.save(bill)
    session.flush()
    
    fetched = bill_repo.get_by_id(bill.id)
    assert fetched is not None
    assert fetched.id == bill.id
    assert fetched.credit_card_id == bill.credit_card_id
    assert fetched.reference_month == bill.reference_month
    assert fetched.due_date == bill.due_date
    assert fetched.previous_balance == bill.previous_balance
    assert fetched.total_amount == bill.total_amount
    assert fetched.is_closed == bill.is_closed
