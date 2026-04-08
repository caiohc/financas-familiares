import uuid
from abc import ABC, abstractmethod
from typing import Optional

from domain.financial.entities import (
    BankAccount,
    CardInstance,
    Category,
    CreditCard,
    Family,
    Income,
    Member,
    Transaction,
)


class FamilyRepository(ABC):
    """Interface (Contrato) para operações de banco de dados com Famílias."""
    @abstractmethod
    def save(self, family: Family) -> None:
        pass

    @abstractmethod
    def get_by_id(self, family_id: uuid.UUID) -> Optional[Family]:
        pass


class MemberRepository(ABC):
    """Interface para gerenciar Membros. O contexto financeiro dita as buscas atreladas à Família."""
    @abstractmethod
    def save(self, member: Member) -> None:
        pass

    @abstractmethod
    def get_by_id(self, member_id: uuid.UUID) -> Optional[Member]:
        pass

    @abstractmethod
    def list_by_family(self, family_id: uuid.UUID) -> list[Member]:
        pass


class CategoryRepository(ABC):
    """Interface para buscar as taxonomias das classificações que provamos serem Globais."""
    @abstractmethod
    def save(self, category: Category) -> None:
        pass

    @abstractmethod
    def get_by_id(self, category_id: uuid.UUID) -> Optional[Category]:
        pass

    @abstractmethod
    def list_all(self) -> list[Category]:
        pass


class BankAccountRepository(ABC):
    """Contrato de leitura e escrita das Contas Bancárias baseadas no isolamento do Tenant(Família)."""
    @abstractmethod
    def save(self, account: BankAccount) -> None:
        pass

    @abstractmethod
    def get_by_id(self, account_id: uuid.UUID) -> Optional[BankAccount]:
        pass

    @abstractmethod
    def list_by_family(self, family_id: uuid.UUID) -> list[BankAccount]:
        pass


class CreditCardRepository(ABC):
    """Contrato que rege a hierarquia do master card e das respectivas instâncias (plásticos)."""
    @abstractmethod
    def save(self, credit_card: CreditCard) -> None:
        """Salva o contrato macro de limite"""
        pass

    @abstractmethod
    def save_instance(self, card_instance: CardInstance) -> None:
        """Salva a cópia/plástico individual"""
        pass

    @abstractmethod
    def list_instances_by_family(self, family_id: uuid.UUID) -> List[CardInstance]:
        pass


class TransactionRepository(ABC):
    """A interface mais densa, encarregada do fluxo atômico financeiro."""
    @abstractmethod
    def save(self, transaction: Transaction) -> None:
        pass

    @abstractmethod
    def get_by_id(self, transaction_id: uuid.UUID) -> Optional[Transaction]:
        pass

    @abstractmethod
    def list_by_family(self, family_id: uuid.UUID) -> List[Transaction]:
        pass

    @abstractmethod
    def list_by_account(self, account_id: uuid.UUID) -> List[Transaction]:
        pass

    @abstractmethod
    def list_by_credit_card_instance(self, card_instance_id: uuid.UUID) -> list[Transaction]:
        pass
