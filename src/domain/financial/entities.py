"""
Subdomínio Financeiro (Orçamento e Organização Familiar)
"""

from decimal import Decimal
import uuid
import re
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

    ASSET = "ASSET"             # Ativos: Conta Bancária, Dinheiro
    LIABILITY = "LIABILITY"     # Passivos: Cartão de Crédito, Fiado


@dataclass(kw_only=True)
class Family:
    """Escopo máximo do controle multi-tenant. Todo o controle financeiro esta vinculado a uma família."""
    
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str
    current_balance: Decimal = Decimal('0.00')

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
    current_balance: Decimal = Decimal('0.00')
    account_type: AccountType = field(init=False)

    def __post_init__(self):

        if not self.family_id:
            raise ValueError("Toda conta deve estar vinculada a uma família.")
        
        if not self.holder_id:
            raise ValueError("Toda conta deve ter um titular.")

        if not self.nickname or not self.nickname.strip():
            raise ValueError("O apelido é obrigatório para uma conta.")
            
        self._validate_balance_invariants()
            
    @abstractmethod
    def _validate_balance_invariants(self):
        """Gancho para as subclasses implementarem regras de consistência de saldo."""
        pass


@dataclass(kw_only=True)
class BankAccount(Account):
    """Uma conta corrente ou poupança em banco ou fintech (Ativo)."""
   
    bank: str
    agency: Optional[str] = None
    account_number: Optional[str] = None
    account_type: AccountType = field(default=AccountType.ASSET, init=False)

    def __post_init__(self):
        super().__post_init__()
        
        if not self.bank or not self.bank.strip():
            raise ValueError("O nome do banco é obrigatório para uma conta bancária.")

    def _validate_balance_invariants(self):
        pass
        

@dataclass(kw_only=True)
class Wallet(Account):
    """Carteira para dinheiro em espécie (Ativo)."""
    
    account_type: AccountType = field(default=AccountType.ASSET, init=False)

    def _validate_balance_invariants(self):
        if self.current_balance < 0:
            raise ValueError("A conta de carteira em espécie não pode ter saldo negativo.")

   
@dataclass(kw_only=True)
class Tab(Account):
    """Conta para despesas no modo fiado/caderneta (Passivo)."""
    account_type: AccountType = field(default=AccountType.LIABILITY, init=False)

    def _validate_balance_invariants(self):
        pass   


@dataclass(kw_only=True)
class CreditCard(Account):
    """Contrato limite de crédito (cartão de crédito) junto à instituição financeira (Passivo)."""
    issuer: Optional[str] = None  # Emissor - quem forneceu o cartão (Banco ou fintech)
    brand: str  # Bandeira do cartão (VISA, Mastercard, Elo, etc)
    tier: Optional[str] = None  # Nível do cartão (Gold, Platinum, Black, etc)
    limit: Decimal = Decimal('0.00')
    due_day: Optional[int] = None  # Dia do mês estipulado para o vencimento da fatura (1 a 31)
    bank_account_id: Optional[uuid.UUID] = None  # Conta a qual o cartão é vinculado

    account_type: AccountType = field(default=AccountType.LIABILITY, init=False)

    def __post_init__(self):
        super().__post_init__()
        
        if not self.brand or not self.brand.strip():
            raise ValueError("A bandeira do cartão de crédito deve ser informada.")

        if (not self.bank_account_id) and (not self.issuer or not self.issuer.strip()):
            raise ValueError("Um cartão de crédito deve ter uma conta bancária vinculada ou um emissor.")

        if self.due_day is not None and (self.due_day < 1 or self.due_day > 31):
            raise ValueError("O dia de vencimento deve ser um valor entre 1 e 31.")
        
    def _validate_balance_invariants(self):
        pass


@dataclass(kw_only=True)
class CardInstance:
    """Plásticos ou Cartões virtuais emitidos a partir de um cartão de crédito."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    credit_card_id: uuid.UUID
    holder_id: uuid.UUID  # Quem tem a posse deste plástico (titular ou dependente)
    nickname: str  

    def __post_init__(self):
        if not self.family_id:
            raise ValueError("O cartão (instância) deve estar associado a uma família.")
        if not self.credit_card_id:
            raise ValueError("O cartão (instância) deve estar associado a um contrato de cartão de crédito mestre.")
        if not self.holder_id:
            raise ValueError("O cartão (instância) deve ter um portador.")


@dataclass(kw_only=True)
class CreditCardBill:
    """Uma fatura de um cartão de crédito."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    credit_card_id: uuid.UUID
    reference_month: str  # Formato YYYY-MM (Ex: 2026-04)
    due_date: date  # Dia exato do vencimento nesse mês específico
    is_closed: bool = False
    total_amount: Decimal = Decimal('0.00')

    def __post_init__(self):
        if not self.family_id:
            raise ValueError("A fatura deve estar associada a uma família.")
        if not self.credit_card_id:
            raise ValueError("A fatura deve estar associada a um contrato de cartão de crédito.")
        if not self.reference_month or not isinstance(self.reference_month, str) or not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", self.reference_month):
            raise ValueError("O mês de referência deve ser informado no formato YYYY-MM.")
        if not self.due_date:
            raise ValueError("A data de vencimento da fatura deve ser informada.")


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
    amount: Decimal
    description: str
    is_forecast: bool = False  # Define se o fluxo é apenas uma previsão futura (orçamento)

    # Vínculo com a conta raiz (Bancária, Caixa, Cartão ou Fiado)
    account_id: uuid.UUID

    # Campos opcionais de rastreabilidade de instrumentos acessórios:
    card_instance_id: Optional[uuid.UUID] = None
    credit_card_bill_id: Optional[uuid.UUID] = None
    transfer_id: Optional[uuid.UUID] = None
    
    # Controle matemático de parcelas
    installment_current: int = 1
    installment_total: int = 1

    def __post_init__(self):
        if not self.family_id:
            raise ValueError("A transação deve pertencer a uma família.")
        if not self.category_id:
            raise ValueError("A transação deve ter uma categoria.")
        if not self.type:
            raise ValueError("A transação deve ter um tipo.")
        if not self.date:
            raise ValueError("A transação deve ter uma data.")
        if self.amount is None:
            raise ValueError("A transação deve ter um valor.")
        if not self.description or not self.description.strip():
            raise ValueError("A transação deve ter uma descrição.")
        if not isinstance(self.is_forecast, bool):
            raise ValueError("A transação deve informar se é uma previsão de forma booleana.")
        if not self.account_id:
            raise ValueError("A transação deve estar associada a uma conta.")

@dataclass(kw_only=True)
class Transfer:
    """Agregado que materializa o evento de transferência entre duas contas."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: Decimal
    date: date
    description: str

    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError("O valor da transferência deve ser maior que zero.")
        if self.source_account_id == self.destination_account_id:
            raise ValueError("A conta de origem e destino não podem ser a mesma.")

    def generate_transactions(self, category_id: uuid.UUID) -> tuple[Transaction, Transaction]:
        """Fabrica o par de transações de saída e entrada espelhadas."""
        out_tx = Transaction(
            family_id=self.family_id,
            account_id=self.source_account_id,
            category_id=category_id,
            type=TransactionType.TRANSFER_OUT,
            date=self.date,
            amount=self.amount,
            description=self.description or "Transferência enviada",
            transfer_id=self.id
        )
        
        in_tx = Transaction(
            family_id=self.family_id,
            account_id=self.destination_account_id,
            category_id=category_id,
            type=TransactionType.TRANSFER_IN,
            date=self.date,
            amount=self.amount,
            description=self.description or "Transferência recebida",
            transfer_id=self.id
        )
        return out_tx, in_tx


@dataclass(kw_only=True)
class MonthlyBalance:
    """O registro do saldo de uma conta ao final de um período (mensal)."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    account_id: uuid.UUID
    reference_month: str  # Ex: '2026-04'
    real_balance: Decimal = Decimal('0.00')
    projected_balance: Decimal = Decimal('0.00')

    def __post_init__(self):
        if not self.account_id:
            raise ValueError("O registro de saldo mensal deve estar associado a uma conta.")
        if not self.reference_month or not isinstance(self.reference_month, str) or not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", self.reference_month):
            raise ValueError("O mês de referência deve ser informado no formato YYYY-MM.")
        if self.real_balance is None or self.projected_balance is None:
            raise ValueError("O registro de saldo mensal deve ter os valores real e projetado.")

    @classmethod
    def create_from_history(
        cls, 
        account_id: uuid.UUID, 
        month: str, 
        previous_real_balance: Decimal, 
        previous_projected_balance: Decimal,
        transactions: list[Transaction]
    ) -> 'MonthlyBalance':
        """
        Factory method que encapsula a regra de negócio do cálculo do saldo.
        A partir de um saldo inicial, soma as receitas e subtrai as despesas.
        Calcula separadamente o saldo real e o saldo projetado (que inclui previsões).
        """
        new_real = previous_real_balance
        new_projected = previous_projected_balance
        
        for tx in transactions:
            # Transferências que saem comportam-se como despesas
            amount = tx.amount
            if tx.type in (TransactionType.EXPENSE, TransactionType.TRANSFER_OUT):
                amount = -amount

            # O saldo projetado sempre recebe a transação (seja real ou previsão)
            new_projected += amount
            
            # O saldo real só recebe a transação se ela NÃO for previsão
            if not tx.is_forecast:
                new_real += amount
                
        return cls(
            account_id=account_id,
            reference_month=month,
            real_balance=new_real,
            projected_balance=new_projected
        )
