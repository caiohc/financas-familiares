"""
Subdomínio Financeiro (Orçamento e Organização Familiar)
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


@dataclass(kw_only=True)
class Family:
    """Escopo máximo do controle multi-tenant. Todo o controle financeiro esta vinculado a uma família."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str
    current_balance: float = 0.0

    def process_transaction(self, transaction: 'Transaction'):
        """Domínio Rico: O próprio objeto atualiza seu saldo cumulativo interpretando a Transação."""
        if (transaction.is_realized and transaction.family_id == self.id
                and not transaction.ignore_in_family_balance):
            if transaction.type == TransactionType.INCOME:
                self.current_balance += transaction.amount
            elif transaction.type == TransactionType.EXPENSE:
                self.current_balance -= transaction.amount


@dataclass(kw_only=True)
class Member:
    """Entidade do domínio financeiro representando um integrante da família,
    que é agente realizador de receita e/ou despesa."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    name: str


class TransactionType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@dataclass(kw_only=True)
class Category:
    """Categoria para organização do orçamento.
    As transações são agrupadas por categorias (Ex: Alimentação, Lazer)."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str
    type: TransactionType


@dataclass(kw_only=True)
class BankAccount:
    """Uma conta corrente ou poupança em banco ou fintech."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    holder_id: uuid.UUID  # Membro da família titular da conta
    nickname: str
    bank: str = ""
    agency: str = ""
    account_number: str = ""
    current_balance: float = 0.0

    def process_transaction(self, transaction: 'Transaction'):
        """Calcula o impacto da transação bancária apenas se ela tiver sido efetivada e pertencer a esta conta."""
        if transaction.is_realized and transaction.bank_account_id == self.id:
            if transaction.type == TransactionType.INCOME:
                self.current_balance += transaction.amount
            elif transaction.type == TransactionType.EXPENSE:
                self.current_balance -= transaction.amount


@dataclass(kw_only=True)
class CreditCard:
    """Contrato limite de crédito (cartão de crédito) junto à instituição financeira."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    holder_id: uuid.UUID  # Quem é o responsável legal do cartão (Member)
    nickname: str  
    issuer: Optional[str] = None  # Emissor - quem forneceu o cartão (Banco ou fintech)
    brand: str  # Bandeira do cartão (VISA, Mastercard, Elo, etc)
    tier: Optional[str] = None  # Nível do cartão (Gold, Platinum, Black, etc)
    limit: float
    due_day: int  # Dia do mês estipulado para o vencimento da fatura (1 a 31)
    bank_account_id: Optional[uuid.UUID] = None  # Conta a qual o cartão é vinculado


@dataclass(kw_only=True)
class CreditCardBill:
    """Uma fatura de um cartão de crédito."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    credit_card_id: uuid.UUID
    reference_month: str  # Formato YYYY-MM (Ex: 2026-04)
    due_date: date  # Dia exato do vencimento nesse mês específico
    is_closed: bool = False
    total_amount: float = 0.0

    def process_transaction(self, transaction: 'Transaction'):
        """Engloba despensas e estornos no domínio matemático da fatura."""
        if transaction.credit_card_bill_id == self.id:
            if transaction.type == TransactionType.EXPENSE:
                self.total_amount += transaction.amount
            elif transaction.type == TransactionType.INCOME:
                self.total_amount -= transaction.amount


@dataclass(kw_only=True)
class CardInstance:
    """Plásticos ou Cartões virtuais emitidos a partir de um cartão de crédito."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    credit_card_id: uuid.UUID
    holder_id: uuid.UUID  # Quem tem a posse deste plástico (Member ou dependente)
    nickname: str  


@dataclass(kw_only=True)
class Transaction:
    """O registro atômico de uma movimentação financeira."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    category_id: uuid.UUID
    type: TransactionType
    date: date  # Data do fluxo  caixa efetivo (quando o dinheiro sai da conta ou a data de vencimento da fatura do cartão)
    amount: float
    description: str
    is_realized: bool = None  # Define se o fluxo realmente acorreu no banco ou se é previsão pendente
    ignore_in_family_balance: bool = False  # Evita a dupla contabilização (Ex: pagamento da fatura do cartão)

    # Campos opcionais de rastreabilidade do instrumento financeiro:
    bank_account_id: Optional[uuid.UUID] = None
    card_instance_id: Optional[uuid.UUID] = None
    credit_card_bill_id: Optional[uuid.UUID] = None
    
    # Controle matemático de parcelas
    installment_current: int = 1
    installment_total: int = 1
