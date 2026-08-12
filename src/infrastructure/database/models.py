import uuid
from typing import Optional, List
from decimal import Decimal
from datetime import date
from sqlalchemy import String, Numeric, Boolean, Date, Enum, ForeignKey, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from domain.financial.entities import TransactionType, AccountType

class Base(DeclarativeBase):
    pass

# Tabela Associativa para N:M entre Faturas e Transferências
bill_transfer_settlements = Table(
    "bill_transfer_settlements",
    Base.metadata,
    Column("bill_id", String(36), ForeignKey("credit_card_bills.id", ondelete="CASCADE"), primary_key=True),
    Column("transfer_id", String(36), ForeignKey("transfers.id", ondelete="CASCADE"), primary_key=True)
)

class FamilyModel(Base):
    __tablename__ = "families"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0.00'), nullable=False)

class MemberModel(Base):
    __tablename__ = "members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

class FamilyCostCenterModel(Base):
    __tablename__ = "family_cost_centers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

class CategoryModel(Base):
    __tablename__ = "categories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)

# -- HIERARQUIA DE CONTAS (Class Table Inheritance) --
class AccountModel(Base):
    __tablename__ = "accounts"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    holder_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    nickname: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0.00'), nullable=False)
    
    # Polimorfismo do SQLAlchemy
    type_identifier: Mapped[str] = mapped_column(String(50))
    __mapper_args__ = {
        "polymorphic_identity": "account",
        "polymorphic_on": "type_identifier",
    }

class BankAccountModel(AccountModel):
    __tablename__ = "bank_accounts"
    id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True)
    bank: Mapped[str] = mapped_column(String(100), nullable=False)
    agency: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    account_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    __mapper_args__ = {"polymorphic_identity": "bank_account"}

class AccountsPayableModel(AccountModel):
    __tablename__ = "accounts_payable"
    id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True)
    __mapper_args__ = {"polymorphic_identity": "accounts_payable"}

class WalletModel(AccountModel):
    __tablename__ = "wallets"
    id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True)
    __mapper_args__ = {"polymorphic_identity": "wallet"}

class CreditCardModel(AccountModel):
    __tablename__ = "credit_cards"
    id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True)
    brand: Mapped[str] = mapped_column(String(50), nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    due_day: Mapped[Optional[int]] = mapped_column(nullable=True)
    tier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    bank_account_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    
    __mapper_args__ = {
        "polymorphic_identity": "credit_card",
        "inherit_condition": id == AccountModel.id
    }

# -- ENTIDADES DEPENDENTES DE CONTAS --
class CardInstanceModel(Base):
    __tablename__ = "card_instances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    credit_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("credit_cards.id", ondelete="CASCADE"), nullable=False)
    card_holder_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    nickname: Mapped[str] = mapped_column(String(255), nullable=False)

class CreditCardBillModel(Base):
    __tablename__ = "credit_card_bills"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    credit_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("credit_cards.id", ondelete="CASCADE"), nullable=False)
    reference_month: Mapped[str] = mapped_column(String(7), nullable=False) # YYYY-MM
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    previous_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0.00'), nullable=False)
    payments_received: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0.00'), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0.00'), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # O mapeamento relacional da lista de IDs de Transferências
    settled_by_transfers: Mapped[List["TransferModel"]] = relationship(
        secondary=bill_transfer_settlements
    )

class TransferModel(Base):
    __tablename__ = "transfers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    source_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    destination_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

class TransactionModel(Base):
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    accrual_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    is_forecast: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    
    # Relacionamentos esparsos (Nullable FKs)
    card_instance_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("card_instances.id", ondelete="SET NULL"), nullable=True)
    credit_card_bill_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("credit_card_bills.id", ondelete="SET NULL"), nullable=True)
    transfer_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transfers.id", ondelete="SET NULL"), nullable=True)
    settled_by_transfer_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transfers.id", ondelete="SET NULL"), nullable=True)
    originating_transaction_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    originating_bill_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("credit_card_bills.id", ondelete="SET NULL"), nullable=True)
    source_transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cost_center_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("family_cost_centers.id", ondelete="SET NULL"), nullable=True)
    
    # Metadados de parcelamento
    installment_current: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    installment_total: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    installment_group_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

class MonthlyBalanceModel(Base):
    __tablename__ = "monthly_balances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    reference_month: Mapped[str] = mapped_column(String(7), nullable=False) # YYYY-MM
    projected_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0.00'))
    real_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0.00'))
