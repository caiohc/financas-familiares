import uuid
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal

@dataclass(kw_only=True)
class CreateBankAccountDTO:
    """Entrada bruta para processar a criação de conta bancária por uma rota isolada."""
    family_id: uuid.UUID
    holder_id: uuid.UUID
    nickname: Optional[str] = None
    bank: str = ""
    agency: str = ""
    account_number: str = ""

@dataclass(kw_only=True)
class CreateCreditCardDTO:
    """Entrada para configurar o contrato Master principal de cartão."""
    family_id: uuid.UUID
    holder_id: uuid.UUID
    nickname: Optional[str] = None
    issuer: Optional[str] = None
    brand: str
    limit: Decimal
    due_day: int
    bank_account_id: Optional[uuid.UUID] = None

@dataclass(kw_only=True)
class CreateCardInstanceDTO:
    family_id: uuid.UUID
    credit_card_id: uuid.UUID
    holder_id: uuid.UUID
    nickname: Optional[str] = None

@dataclass(kw_only=True)
class CreateCreditCardBillDTO:
    credit_card_id: uuid.UUID
    reference_month: str
    due_date: 'datetime.date'

@dataclass(kw_only=True)
class CreateTransactionDTO:
    family_id: uuid.UUID
    category_id: uuid.UUID
    type_str: str  # "INCOME" ou "EXPENSE"
    date: 'datetime.date'
    amount: Decimal
    description: str
    
    bank_account_id: Optional[uuid.UUID] = None
    
    # Mapeamento do ecossistema de cartão
    credit_card_id: Optional[uuid.UUID] = None
    card_instance_id: Optional[uuid.UUID] = None
    credit_card_bill_id: Optional[uuid.UUID] = None
    
    installment_total: int = 1
