import uuid
from dataclasses import dataclass

@dataclass(kw_only=True)
class CreateBankAccountDTO:
    """Entrada bruta para processar a criação de conta bancária por uma rota isolada."""
    family_id: uuid.UUID
    holder_id: uuid.UUID
    name: str

@dataclass(kw_only=True)
class CreateCreditCardDTO:
    """Entrada para configurar o contrato Master principal de cartão."""
    family_id: uuid.UUID
    holder_id: uuid.UUID
    name: str
    limit: float
    due_day: int

@dataclass(kw_only=True)
class CreateCardInstanceDTO:
    """Entrada que embasa a criação do plástico atrelado, exigindo a cópia raiz."""
    credit_card_id: uuid.UUID
    holder_id: uuid.UUID # Pode ser o membro titular e original, ou seu dependente da família
    nickname: str
