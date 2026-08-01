from decimal import Decimal
import uuid
from dataclasses import dataclass, field

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
    """Entidade do domínio representando um integrante da família,
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
class FamilyCostCenter:
    """Centro de custo familiar. Agrupador lógico para transações (ex: Núcleo Sogra, Casa de Praia, Filhos).
    Permite visualizar o DRE e o fluxo de caixa particionado sem quebrar a unicidade da conta bancária."""
    
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    name: str
    description: str = ""

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Nome do centro de custo é obrigatório.")
        
        if not self.family_id:
            raise ValueError("O centro de custo deve pertencer a uma família.")
