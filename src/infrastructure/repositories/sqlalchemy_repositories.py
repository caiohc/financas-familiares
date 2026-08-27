import uuid
from typing import Optional, List
from sqlalchemy.orm import Session

from domain.family.entities import Family, Member
from domain.financial.entities import (
    Category, BankAccount, CreditCard, CardInstance, 
    Transaction, CreditCardBill, TransactionType
)
from domain.financial.repositories import (
    FamilyRepository, MemberRepository, CategoryRepository, 
    BankAccountRepository, CreditCardRepository, TransactionRepository, CreditCardBillRepository
)
from infrastructure.database.models import (
    FamilyModel, MemberModel, CategoryModel, BankAccountModel, 
    CreditCardModel, CardInstanceModel, TransactionModel, CreditCardBillModel, TransferModel
)

class SQLAlchemyFamilyRepository(FamilyRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: FamilyModel) -> Family:
        return Family(
            id=uuid.UUID(model.id),
            name=model.name,
            current_balance=model.current_balance
        )

    def _to_model(self, entity: Family) -> FamilyModel:
        return FamilyModel(
            id=str(entity.id),
            name=entity.name,
            current_balance=entity.current_balance
        )

    def save(self, family: Family) -> None:
        model = self._to_model(family)
        self.session.merge(model)
        self.session.flush()

    def get_by_id(self, family_id: uuid.UUID) -> Optional[Family]:
        model = self.session.get(FamilyModel, str(family_id))
        return self._to_domain(model) if model else None

    def list_all(self) -> list[Family]:
        models = self.session.query(FamilyModel).all()
        return [self._to_domain(m) for m in models]

    def delete(self, family_id: uuid.UUID) -> None:
        model = self.session.get(FamilyModel, str(family_id))
        if model:
            self.session.delete(model)
            self.session.flush()

    def has_dependencies(self, family_id: uuid.UUID) -> bool:
        return self.session.query(MemberModel).filter_by(family_id=str(family_id)).first() is not None

class SQLAlchemyMemberRepository(MemberRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: MemberModel) -> Member:
        return Member(
            id=uuid.UUID(model.id),
            family_id=uuid.UUID(model.family_id),
            name=model.name
        )

    def _to_model(self, entity: Member) -> MemberModel:
        return MemberModel(
            id=str(entity.id),
            family_id=str(entity.family_id),
            name=entity.name
        )

    def save(self, member: Member) -> None:
        model = self._to_model(member)
        self.session.merge(model)
        self.session.flush()

    def get_by_id(self, member_id: uuid.UUID) -> Optional[Member]:
        model = self.session.get(MemberModel, str(member_id))
        return self._to_domain(model) if model else None

    def list_by_family(self, family_id: uuid.UUID) -> list[Member]:
        models = self.session.query(MemberModel).filter_by(family_id=str(family_id)).all()
        return [self._to_domain(m) for m in models]

    def list_all(self) -> list[Member]:
        models = self.session.query(MemberModel).all()
        return [self._to_domain(m) for m in models]

    def delete(self, member_id: uuid.UUID) -> None:
        model = self.session.get(MemberModel, str(member_id))
        if model:
            self.session.delete(model)
            self.session.flush()

    def has_dependencies(self, member_id: uuid.UUID) -> bool:
        from infrastructure.database.models import AccountModel
        return self.session.query(AccountModel).filter_by(holder_id=str(member_id)).first() is not None

class SQLAlchemyCategoryRepository(CategoryRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: CategoryModel) -> Category:
        return Category(
            id=uuid.UUID(model.id),
            name=model.name,
            type=model.type
        )

    def _to_model(self, entity: Category) -> CategoryModel:
        return CategoryModel(
            id=str(entity.id),
            name=entity.name,
            type=entity.type
        )

    def save(self, category: Category) -> None:
        model = self._to_model(category)
        self.session.merge(model)
        self.session.flush()

    def get_by_id(self, category_id: uuid.UUID) -> Optional[Category]:
        model = self.session.get(CategoryModel, str(category_id))
        return self._to_domain(model) if model else None

    def list_all(self) -> list[Category]:
        models = self.session.query(CategoryModel).all()
        return [self._to_domain(m) for m in models]

class SQLAlchemyBankAccountRepository(BankAccountRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: BankAccountModel) -> BankAccount:
        return BankAccount(
            id=uuid.UUID(model.id),
            family_id=uuid.UUID(model.family_id),
            holder_id=uuid.UUID(model.holder_id) if model.holder_id else None,
            nickname=model.nickname,
            current_balance=model.current_balance,
            bank=model.bank,
            agency=model.agency,
            account_number=model.account_number
        )

    def _to_model(self, entity: BankAccount) -> BankAccountModel:
        return BankAccountModel(
            id=str(entity.id),
            family_id=str(entity.family_id),
            holder_id=str(entity.holder_id) if entity.holder_id else None,
            nickname=entity.nickname,
            account_type=entity.account_type,
            current_balance=entity.current_balance,
            bank=entity.bank,
            agency=entity.agency,
            account_number=entity.account_number
        )

    def save(self, account: BankAccount) -> None:
        model = self._to_model(account)
        self.session.merge(model)
        self.session.flush()

    def get_by_id(self, account_id: uuid.UUID) -> Optional[BankAccount]:
        model = self.session.get(BankAccountModel, str(account_id))
        return self._to_domain(model) if model else None

    def list_by_family(self, family_id: uuid.UUID) -> list[BankAccount]:
        models = self.session.query(BankAccountModel).filter_by(family_id=str(family_id)).all()
        return [self._to_domain(m) for m in models]

    def list_all(self) -> list[BankAccount]:
        models = self.session.query(BankAccountModel).all()
        return [self._to_domain(m) for m in models]

    def delete(self, account_id: uuid.UUID) -> None:
        model = self.session.get(BankAccountModel, str(account_id))
        if model:
            self.session.delete(model)
            self.session.flush()

class SQLAlchemyCreditCardRepository(CreditCardRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain_credit_card(self, model: CreditCardModel) -> CreditCard:
        return CreditCard(
            id=uuid.UUID(model.id),
            family_id=uuid.UUID(model.family_id),
            holder_id=uuid.UUID(model.holder_id) if model.holder_id else None,
            nickname=model.nickname,
            brand=model.brand,
            issuer=model.issuer,
            tier=model.tier,
            due_day=model.due_day,
            limit=model.limit,
            bank_account_id=uuid.UUID(model.bank_account_id) if model.bank_account_id else None
        )

    def _to_model_credit_card(self, entity: CreditCard) -> CreditCardModel:
        return CreditCardModel(
            id=str(entity.id),
            family_id=str(entity.family_id),
            holder_id=str(entity.holder_id) if entity.holder_id else None,
            nickname=entity.nickname,
            account_type=entity.account_type,
            brand=entity.brand,
            issuer=entity.issuer,
            tier=entity.tier,
            due_day=entity.due_day,
            limit=entity.limit,
            bank_account_id=str(entity.bank_account_id) if entity.bank_account_id else None
        )

    def _to_domain_instance(self, model: CardInstanceModel) -> CardInstance:
        return CardInstance(
            id=uuid.UUID(model.id),
            credit_card_id=uuid.UUID(model.credit_card_id),
            card_holder_id=uuid.UUID(model.card_holder_id),
            nickname=model.nickname,
            last_four_digits=model.last_four_digits,
            is_active=model.is_active
        )

    def _to_model_instance(self, entity: CardInstance) -> CardInstanceModel:
        return CardInstanceModel(
            id=str(entity.id),
            credit_card_id=str(entity.credit_card_id),
            card_holder_id=str(entity.card_holder_id),
            nickname=entity.nickname,
            last_four_digits=entity.last_four_digits,
            is_active=entity.is_active
        )

    def save(self, credit_card: CreditCard) -> None:
        model = self._to_model_credit_card(credit_card)
        self.session.merge(model)
        self.session.flush()

    def save_instance(self, card_instance: CardInstance) -> None:
        model = self._to_model_instance(card_instance)
        self.session.merge(model)
        self.session.flush()

    def list_instances_by_family(self, family_id: uuid.UUID) -> List[CardInstance]:
        models = self.session.query(CardInstanceModel).join(CreditCardModel).filter(CreditCardModel.family_id == str(family_id)).all()
        return [self._to_domain_instance(m) for m in models]

    def get_by_id(self, credit_card_id: uuid.UUID) -> Optional[CreditCard]:
        model = self.session.get(CreditCardModel, str(credit_card_id))
        return self._to_domain_credit_card(model) if model else None

    def list_all(self) -> list[CreditCard]:
        models = self.session.query(CreditCardModel).all()
        return [self._to_domain_credit_card(m) for m in models]

    def list_all_instances(self) -> list[CardInstance]:
        models = self.session.query(CardInstanceModel).all()
        return [self._to_domain_instance(m) for m in models]

    def get_instance_by_id(self, instance_id: uuid.UUID) -> Optional[CardInstance]:
        model = self.session.get(CardInstanceModel, str(instance_id))
        return self._to_domain_instance(model) if model else None

    def delete(self, credit_card_id: uuid.UUID) -> None:
        model = self.session.get(CreditCardModel, str(credit_card_id))
        if model:
            self.session.delete(model)
            self.session.flush()

    def delete_instance(self, instance_id: uuid.UUID) -> None:
        model = self.session.get(CardInstanceModel, str(instance_id))
        if model:
            self.session.delete(model)
            self.session.flush()

class SQLAlchemyCreditCardBillRepository(CreditCardBillRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: CreditCardBillModel) -> CreditCardBill:
        return CreditCardBill(
            id=uuid.UUID(model.id),
            family_id=uuid.UUID(model.family_id),
            credit_card_id=uuid.UUID(model.credit_card_id),
            reference_month=model.reference_month,
            due_date=model.due_date,
            previous_balance=model.previous_balance,
            payments_received=model.payments_received,
            total_amount=model.total_amount,
            is_closed=model.is_closed,
            settled_by_transfer_ids=[uuid.UUID(t.id) for t in model.settled_by_transfers]
        )

    def _to_model(self, entity: CreditCardBill) -> CreditCardBillModel:
        # Busca as transferências reais no banco baseadas na lista de IDs
        transfers = []
        if entity.settled_by_transfer_ids:
            transfer_ids = [str(uid) for uid in entity.settled_by_transfer_ids]
            transfers = self.session.query(TransferModel).filter(TransferModel.id.in_(transfer_ids)).all()
            
        return CreditCardBillModel(
            id=str(entity.id),
            family_id=str(entity.family_id),
            credit_card_id=str(entity.credit_card_id),
            reference_month=entity.reference_month,
            due_date=entity.due_date,
            previous_balance=entity.previous_balance,
            payments_received=entity.payments_received,
            total_amount=entity.total_amount,
            is_closed=entity.is_closed,
            settled_by_transfers=transfers
        )

    def save(self, bill: CreditCardBill) -> None:
        model = self._to_model(bill)
        self.session.merge(model)
        self.session.flush()

    def get_by_id(self, bill_id: uuid.UUID) -> Optional[CreditCardBill]:
        model = self.session.get(CreditCardBillModel, str(bill_id))
        return self._to_domain(model) if model else None
    
    def get_by_card_and_month(self, card_id: uuid.UUID, reference_month: str) -> Optional[CreditCardBill]:
        model = self.session.query(CreditCardBillModel).filter_by(
            credit_card_id=str(card_id), 
            reference_month=reference_month
        ).first()
        return self._to_domain(model) if model else None

class SQLAlchemyTransactionRepository(TransactionRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: TransactionModel) -> Transaction:
        return Transaction(
            id=uuid.UUID(model.id),
            family_id=uuid.UUID(model.family_id),
            category_id=uuid.UUID(model.category_id),
            type=model.type,
            accrual_date=model.accrual_date,
            due_date=model.due_date,
            amount=model.amount,
            description=model.description,
            is_forecast=model.is_forecast,
            account_id=uuid.UUID(model.account_id),
            card_instance_id=uuid.UUID(model.card_instance_id) if model.card_instance_id else None,
            credit_card_bill_id=uuid.UUID(model.credit_card_bill_id) if model.credit_card_bill_id else None,
            transfer_id=uuid.UUID(model.transfer_id) if model.transfer_id else None,
            settled_by_transfer_id=uuid.UUID(model.settled_by_transfer_id) if model.settled_by_transfer_id else None,
            originating_transaction_id=uuid.UUID(model.originating_transaction_id) if model.originating_transaction_id else None,
            originating_bill_id=uuid.UUID(model.originating_bill_id) if model.originating_bill_id else None,
            source_transaction_id=model.source_transaction_id,
            cost_center_id=uuid.UUID(model.cost_center_id) if model.cost_center_id else None,
            installment_current=model.installment_current,
            installment_total=model.installment_total,
            installment_group_id=uuid.UUID(model.installment_group_id) if model.installment_group_id else None
        )

    def _to_model(self, entity: Transaction) -> TransactionModel:
        return TransactionModel(
            id=str(entity.id),
            family_id=str(entity.family_id),
            category_id=str(entity.category_id),
            type=entity.type,
            accrual_date=entity.accrual_date,
            due_date=entity.due_date,
            amount=entity.amount,
            description=entity.description,
            is_forecast=entity.is_forecast,
            account_id=str(entity.account_id),
            card_instance_id=str(entity.card_instance_id) if entity.card_instance_id else None,
            credit_card_bill_id=str(entity.credit_card_bill_id) if entity.credit_card_bill_id else None,
            transfer_id=str(entity.transfer_id) if entity.transfer_id else None,
            settled_by_transfer_id=str(entity.settled_by_transfer_id) if entity.settled_by_transfer_id else None,
            originating_transaction_id=str(entity.originating_transaction_id) if entity.originating_transaction_id else None,
            originating_bill_id=str(entity.originating_bill_id) if entity.originating_bill_id else None,
            source_transaction_id=entity.source_transaction_id,
            cost_center_id=str(entity.cost_center_id) if entity.cost_center_id else None,
            installment_current=entity.installment_current,
            installment_total=entity.installment_total,
            installment_group_id=str(entity.installment_group_id) if entity.installment_group_id else None
        )

    def save(self, transaction: Transaction) -> None:
        model = self._to_model(transaction)
        self.session.merge(model)
        self.session.flush()

    def get_by_id(self, transaction_id: uuid.UUID) -> Optional[Transaction]:
        model = self.session.get(TransactionModel, str(transaction_id))
        return self._to_domain(model) if model else None

    def list_by_family(self, family_id: uuid.UUID) -> List[Transaction]:
        models = self.session.query(TransactionModel).filter_by(family_id=str(family_id)).all()
        return [self._to_domain(m) for m in models]

    def list_by_account(self, account_id: uuid.UUID) -> List[Transaction]:
        models = self.session.query(TransactionModel).filter_by(account_id=str(account_id)).all()
        return [self._to_domain(m) for m in models]

    def list_by_credit_card_instance(self, card_instance_id: uuid.UUID) -> list[Transaction]:
        models = self.session.query(TransactionModel).filter_by(card_instance_id=str(card_instance_id)).all()
        return [self._to_domain(m) for m in models]
