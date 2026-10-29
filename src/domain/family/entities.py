from decimal import Decimal
import uuid
from dataclasses import dataclass, field
from typing import Optional

from domain.shared.exceptions import DomainValidationError

def _required_name(name: Optional[str], error_message: str) -> str:
    if not name or not name.strip():
        raise DomainValidationError("name", error_message)
    return name.strip()


@dataclass(kw_only=True)
class Family:
    """Escopo máximo do controle multi-tenant. Todo o controle financeiro esta vinculado a uma família."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str
    current_balance: Decimal = Decimal('0.00')

    @staticmethod
    def normalize_name(name: Optional[str]) -> str:
        return _required_name(name, "Nome da família é obrigatório.")

    def __post_init__(self):
        self.name = self.normalize_name(self.name)

    def rename(self, new_name: Optional[str]) -> None:
        self.name = self.normalize_name(new_name)


@dataclass(kw_only=True)
class Member:
    """Entidade do domínio representando um integrante da família,
    que é agente realizador de receita e/ou despesa."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    name: str

    @staticmethod
    def normalize_name(name: Optional[str]) -> str:
        return _required_name(name, "Nome do membro é obrigatório.")

    def __post_init__(self):
        self.name = self.normalize_name(self.name)

        if not self.family_id:
            raise DomainValidationError("family_id", "Membro deve pertencer a uma família.")

    def rename(self, new_name: Optional[str]) -> None:
        self.name = self.normalize_name(new_name)


@dataclass(kw_only=True)
class FamilyCostCenter:
    """Centro de custo familiar. Agrupador lógico para transações (ex: Núcleo Sogra, Casa de Praia, Filhos).
    Permite visualizar o DRE e o fluxo de caixa particionado sem quebrar a unicidade da conta bancária."""
    
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    family_id: uuid.UUID
    name: str
    description: Optional[str] = None

    @staticmethod
    def normalize_name(name: Optional[str]) -> str:
        return _required_name(name, "Nome do centro de custo é obrigatório.")

    def __post_init__(self):
        self.name = self.normalize_name(self.name)

        if not self.family_id:
            raise DomainValidationError("family_id", "O centro de custo deve pertencer a uma família.")

    def rename(self, new_name: Optional[str]) -> None:
        self.name = self.normalize_name(new_name)
