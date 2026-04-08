"""
Subdomínio Financeiro (Orçamento e Organização Familiar)
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class TransactionType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@dataclass(kw_only=True)
class Family:
    """Escopo máximo do controle multi-tenant."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str


@dataclass(kw_only=True)
class Member:
    """Entidade do domínio financeiro representando o componente de gerência da família."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    name: str


@dataclass(kw_only=True)
class Category:
    """Categoria para organização do orçamento (Ex: Alimentação, Lazer)."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str
    type: TransactionType


@dataclass(kw_only=True)
class BankAccount:
    """Uma conta corrente ou poupança."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    holder_id: uuid.UUID  # Obrigatório apontar para a entidade Member
    name: str  # Ex: "Conta Corrente Itaú"


@dataclass(kw_only=True)
class CreditCard:
    """Contrato Master de Limite de Crédito junto à instituição financeira."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    holder_id: uuid.UUID  # Quem é o responsável legal do cartão (Member)
    name: str  
    limit: float


@dataclass(kw_only=True)
class CardInstance:
    """Plásticos ou Cartões virtuais emitidos a partir de um CreditCard."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    credit_card_id: uuid.UUID
    holder_id: uuid.UUID  # Quem tem a posse deste plástico (Member ou dependente)
    nickname: str  


@dataclass(kw_only=True)
class Income:
    """Controle de entradas mensais esperadas de dinheiro."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    name: str  
    expected_amount: float
    holder_id: Optional[uuid.UUID] = None  # Se None, pertence à família genericamente


@dataclass(kw_only=True)
class Transaction:
    """O registro atômico de uma movimentação financeira."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    category_id: uuid.UUID
    type: TransactionType
    date: date
    amount: float
    description: str

    # Um dos 3 deve ser preenchido (ou todos None para Dinheiro Físico/Caixa):
    bank_account_id: Optional[uuid.UUID] = None
    card_instance_id: Optional[uuid.UUID] = None
    income_id: Optional[uuid.UUID] = None  # Pertinente apenas se for uma Transação vinculada a Income
