from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import String, Numeric, Boolean, Date, Enum, ForeignKey, Table, Column, Integer, Index, CheckConstraint, DateTime, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from domain.financial.entities import TransactionType, AccountType
from domain.identity.entities import Role
from domain.identity.invitations import InvitationPurpose

class Base(DeclarativeBase):
    pass

# Tabela Associativa para N:M entre Faturas e Transferências
bill_transfer_settlements = Table(
    "bill_transfer_settlements",
    Base.metadata,
    Column("bill_id", String(36), ForeignKey("credit_card_bills.id", ondelete="CASCADE"), primary_key=True),
    Column("transfer_id", String(36), ForeignKey("transfers.id", ondelete="CASCADE"), primary_key=True)
)

import infrastructure.database.sqlite_functions  # noqa: F401  (registra fold() no SQLite)


class FamilyModel(Base):
    __tablename__ = "families"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0.00'), nullable=False)

    __table_args__ = (
        # Nome não é único (várias famílias podem se chamar "Silva"); o índice
        # sobre lower(name) existe só para acelerar busca e ordenação.
        Index("ix_families_name_lower", func.lower(name)),
    )

class MemberModel(Base):
    __tablename__ = "members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        # Nome único por família (case-insensitive), famílias diferentes podem repetir nomes.
        Index("ix_members_family_id_name_lower", "family_id", func.lower(name), unique=True),
    )

class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    # Nulo apenas para os papéis de nível de sistema (ROOT e SYSTEM_ADMIN).
    family_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=True)
    # Nome da pessoa. Nulo apenas para o ROOT, que não representa uma pessoa.
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nulo enquanto a pessoa não definiu a senha (conta pendente) ou após a redefinição administrativa.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("1"))
    # Nulo = nunca ativada (o e-mail ainda não é confiável).
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        # username e email são únicos globalmente (cada um por si, não composto), case-insensitive.
        Index("ix_users_username_lower", func.lower(username), unique=True),
        Index("ix_users_email_lower", func.lower(email), unique=True),
        Index("ix_users_family_id", "family_id"),
        # Rede de segurança das invariantes do domínio: família nula <=> papel de nível de sistema;
        # nome obrigatório para todos, exceto o ROOT.
        CheckConstraint(
            "(role IN ('ROOT', 'SYSTEM_ADMIN') AND family_id IS NULL) OR (role NOT IN ('ROOT', 'SYSTEM_ADMIN') AND family_id IS NOT NULL)",
            name="ck_users_role_family",
        ),
        CheckConstraint("role = 'ROOT' OR (name IS NOT NULL AND trim(name) <> '')", name="ck_users_name_required"),
        # Quem tem senha foi ativado; o root sempre tem senha.
        CheckConstraint("password_hash IS NULL OR activated_at IS NOT NULL", name="ck_users_password_requires_activation"),
        CheckConstraint("role <> 'ROOT' OR password_hash IS NOT NULL", name="ck_users_root_has_password"),
    )

class UserInvitationModel(Base):
    """Convites de ativação, redefinição e recuperação. Token e código só em hash."""
    __tablename__ = "user_invitations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    purpose: Mapped[InvitationPurpose] = mapped_column(Enum(InvitationPurpose), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    code_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Só informativo (quem emitiu). Não é chave estrangeira: apagar quem emitiu não pode ser barrado por isto.
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ux_user_invitations_token_hash", "token_hash", unique=True),
        # No máximo um convite ativo (nem consumido nem revogado) por usuário.
        Index(
            "ux_user_invitations_one_active_per_user", "user_id", unique=True,
            sqlite_where=text("consumed_at IS NULL AND revoked_at IS NULL"),
        ),
        # Convites de ativação e de redefinição exigem código; o de recuperação não tem.
        CheckConstraint(
            "(purpose = 'RECOVERY' AND code_hash IS NULL) OR (purpose <> 'RECOVERY' AND code_hash IS NOT NULL)",
            name="ck_user_invitations_code_by_purpose",
        ),
    )


class FamilyCostCenterModel(Base):
    __tablename__ = "family_cost_centers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        # Nome único por família (case-insensitive), famílias diferentes podem repetir nomes.
        Index("ix_family_cost_centers_family_id_name_lower", "family_id", func.lower(name), unique=True),
    )

class CategoryModel(Base):
    __tablename__ = "categories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)

    __table_args__ = (
        # Categorias são globais: nome único em toda a base (case-insensitive), independente do tipo.
        Index("ix_categories_name_lower", func.lower(name), unique=True),
    )

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
    agency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
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
    issuer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_day: Mapped[int | None] = mapped_column(nullable=True)
    tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    bank_account_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    
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
    settled_by_transfers: Mapped[list["TransferModel"]] = relationship(
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
    card_instance_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("card_instances.id", ondelete="SET NULL"), nullable=True)
    credit_card_bill_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("credit_card_bills.id", ondelete="SET NULL"), nullable=True)
    transfer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("transfers.id", ondelete="SET NULL"), nullable=True)
    settled_by_transfer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("transfers.id", ondelete="SET NULL"), nullable=True)
    originating_transaction_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    originating_bill_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("credit_card_bills.id", ondelete="SET NULL"), nullable=True)
    source_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cost_center_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("family_cost_centers.id", ondelete="SET NULL"), nullable=True)
    
    # Metadados de parcelamento
    installment_current: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    installment_total: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    installment_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

class MonthlyBalanceModel(Base):
    __tablename__ = "monthly_balances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    reference_month: Mapped[str] = mapped_column(String(7), nullable=False) # YYYY-MM
    projected_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0.00'))
    real_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0.00'))
