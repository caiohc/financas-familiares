"""
Subdomínio Financeiro (Orçamento e Organização Familiar)
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class TransactionType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


class AccountType(Enum):
    ASSET = "ASSET"       # Ativos: Conta Bancária, Dinheiro
    LIABILITY = "LIABILITY" # Passivos: Cartão de Crédito, Fiado


@dataclass(kw_only=True)
class Family:
    """Escopo máximo do controle multi-tenant. Todo o controle financeiro esta vinculado a uma família."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str
    current_balance: float = 0.0

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Nome da família é obrigatório.")


@dataclass(kw_only=True)
class Member:
    """Entidade do domínio financeiro representando um integrante da família,
    que é agente realizador de receita e/ou despesa."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    name: str

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Nome do membro é obrigatório.")
        if not self.family_id:
            raise ValueError("Membro deve pertencer a uma família.")


@dataclass(kw_only=True)
class Account(ABC):
    """Superclasse abstrata para Contas Patrimoniais."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    holder_id: uuid.UUID  # Membro da família titular da conta
    nickname: str
    current_balance: float = 0.0
    account_type: AccountType = field(init=False)

    def __post_init__(self):
        if not self.family_id:
            raise ValueError("Toda conta deve estar vinculada a uma família.")
        if not self.holder_id:
            raise ValueError("Toda conta deve ter um titular.")
            
    @abstractmethod
    def _validate_balance_invariants(self):
        """Gancho para as subclasses implementarem regras de consistência de saldo."""
        pass


@dataclass(kw_only=True)
class BankAccount(Account):
    """Uma conta corrente ou poupança em banco ou fintech (Ativo)."""
    bank: str = ""
    agency: str = ""
    account_number: str = ""

    def __post_init__(self):
        self.account_type = AccountType.ASSET
        super().__post_init__()
        if not self.bank or not self.bank.strip():
            raise ValueError("O nome do banco (bank) é obrigatório para uma BankAccount.")

    def _validate_balance_invariants(self):
        pass

    @classmethod
    def create(cls, *, family_id: uuid.UUID, holder_id: uuid.UUID, holder_name: str, 
               bank: str, agency: str = "", account_number: str = "", nickname: Optional[str] = None) -> 'BankAccount':
        """Método de Fábrica que encapsula a regra de criação e apelido padrão."""
        if not nickname or not nickname.strip():
            primeiro_nome = holder_name.split()[0] if holder_name else ''
            if primeiro_nome:
                nickname = f"{bank} ({primeiro_nome})"
            else:
                nickname = bank

        return cls(
            family_id=family_id,
            holder_id=holder_id,
            nickname=nickname,
            bank=bank,
            agency=agency,
            account_number=account_number
        )


@dataclass(kw_only=True)
class CashAccount(Account):
    """Conta para dinheiro em espécie (Ativo)."""
    
    def __post_init__(self):
        self.account_type = AccountType.ASSET
        super().__post_init__()
        self._validate_balance_invariants()

    def _validate_balance_invariants(self):
        if self.current_balance < 0:
            raise ValueError("A conta de dinheiro em espécie não pode ter saldo negativo.")

    @classmethod
    def create(cls, *, family_id: uuid.UUID, holder_id: uuid.UUID, holder_name: str, 
               nickname: Optional[str] = None) -> 'CashAccount':
        """Método de Fábrica que encapsula a regra de criação e apelido padrão."""
        if not nickname or not nickname.strip():
            primeiro_nome = holder_name.split()[0] if holder_name else ''
            if primeiro_nome:
                nickname = f"Espécie ({primeiro_nome})"
            else:
                nickname = "Espécie"

        return cls(
            family_id=family_id,
            holder_id=holder_id,
            nickname=nickname
        )


@dataclass(kw_only=True)
class TabAccount(Account):
    """Conta para despesas no modo fiado/caderneta (Passivo)."""
    
    def __post_init__(self):
        self.account_type = AccountType.LIABILITY
        super().__post_init__()

    def _validate_balance_invariants(self):
        pass

    @classmethod
    def create(cls, *, family_id: uuid.UUID, holder_id: uuid.UUID, holder_name: str, 
               nickname: Optional[str] = None) -> 'TabAccount':
        """Método de Fábrica que encapsula a regra de criação e apelido padrão."""
        if not nickname or not nickname.strip():
            primeiro_nome = holder_name.split()[0] if holder_name else ''
            if primeiro_nome:
                nickname = f"Fiado ({primeiro_nome})"
            else:
                nickname = "Fiado"

        return cls(
            family_id=family_id,
            holder_id=holder_id,
            nickname=nickname
        )


@dataclass(kw_only=True)
class CreditCard(Account):
    """Contrato limite de crédito (cartão de crédito) junto à instituição financeira (Passivo)."""
    issuer: Optional[str] = None  # Emissor - quem forneceu o cartão (Banco ou fintech)
    brand: str  # Bandeira do cartão (VISA, Mastercard, Elo, etc)
    tier: Optional[str] = None  # Nível do cartão (Gold, Platinum, Black, etc)
    limit: float = 0.0
    due_day: Optional[int] = None  # Dia do mês estipulado para o vencimento da fatura (1 a 31)
    bank_account_id: Optional[uuid.UUID] = None  # Conta a qual o cartão é vinculado

    def __post_init__(self):
        self.account_type = AccountType.LIABILITY
        super().__post_init__()
        
        if not self.brand or not self.brand.strip():
            raise ValueError("A bandeira do cartão de crédito deve ser informada.")

        if (not self.bank_account_id or not self.holder_id) and (not self.issuer):
            raise ValueError("Um cartão de crédito deve ter uma conta bancária vinculada ou um emissor.")
        
    def _validate_balance_invariants(self):
        pass

    @classmethod
    def create(cls, *, family_id: uuid.UUID, holder_id: uuid.UUID,
               brand: str, limit: float, due_day: int,
               issuer: Optional[str] = None, tier: Optional[str] = None,
               bank_account_id: Optional[uuid.UUID] = None,
               bank_account_nickname: Optional[str] = None,
               nickname: Optional[str] = None) -> 'CreditCard':
        """Método de Fábrica que encapsula a regra de criação e apelidos padrão."""

        # Lógica do Nickname (O issuer, se houver fallback com a BankAccount, 
        # já deve vir preenchido pela camada de Serviço)
        if not nickname or not nickname.strip():
            tier_str = f" {tier.strip()}" if tier and tier.strip() else ""
            card_part = f"{brand.strip()}{tier_str}"
            
            if issuer and issuer.strip():
                nickname = f"{issuer.strip()} - {card_part}"
            elif bank_account_nickname and bank_account_nickname.strip():
                nickname = f"{bank_account_nickname} - {card_part}"
            else:
                nickname = card_part

        return cls(
            family_id=family_id,
            holder_id=holder_id,
            nickname=nickname,
            issuer=issuer,
            brand=brand,
            tier=tier,
            limit=limit,
            due_day=due_day,
            bank_account_id=bank_account_id
        )


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


@dataclass(kw_only=True)
class CardInstance:
    """Plásticos ou Cartões virtuais emitidos a partir de um cartão de crédito."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    credit_card_id: uuid.UUID
    holder_id: uuid.UUID  # Quem tem a posse deste plástico (Member ou dependente)
    nickname: str  


@dataclass(kw_only=True)
class Category:
    """Categoria para organização do orçamento.
    As transações são agrupadas por categorias (Ex: Alimentação, Lazer)."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str
    type: TransactionType

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Nome da categoria é obrigatório.")
        if not self.type:
            raise ValueError("Tipo da categoria é obrigatório.")


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

    # Vínculo com a conta raiz (Bancária, Caixa, Cartão ou Fiado)
    account_id: Optional[uuid.UUID] = None

    # Campos opcionais de rastreabilidade de instrumentos acessórios:
    card_instance_id: Optional[uuid.UUID] = None
    credit_card_bill_id: Optional[uuid.UUID] = None
    
    # Controle matemático de parcelas
    installment_current: int = 1
    installment_total: int = 1
