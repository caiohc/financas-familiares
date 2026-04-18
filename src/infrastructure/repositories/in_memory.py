import uuid
from typing import Optional

from domain.financial.entities import (
    BankAccount, CardInstance, CreditCard, Family, Member, Transaction, CreditCardBill
)
from domain.financial.repositories import (
    BankAccountRepository, CreditCardRepository, FamilyRepository, 
    MemberRepository, TransactionRepository, CreditCardBillRepository
)


class FamilyMemoryRepository(FamilyRepository):
    """A chave principal da tabela fake é o próprio ID da Entidade."""
    def __init__(self):
        self._data: dict[uuid.UUID, Family] = {}

    def save(self, family: Family) -> None:
        self._data[family.id] = family

    def get_by_id(self, family_id: uuid.UUID) -> Optional[Family]:
        return self._data.get(family_id, None)

    def list_all(self) -> list[Family]:
        return list(self._data.values())


class MemberMemoryRepository(MemberRepository):
    def __init__(self):
        self._data: dict[uuid.UUID, Member] = {}

    def save(self, member: Member) -> None:
        self._data[member.id] = member

    def get_by_id(self, member_id: uuid.UUID) -> Optional[Member]:
        return self._data.get(member_id, None)

    def list_by_family(self, family_id: uuid.UUID) -> list[Member]:
        return [m for m in self._data.values() if m.family_id == family_id]

    def list_all(self) -> list[Member]:
        return list(self._data.values())


class BankAccountMemoryRepository(BankAccountRepository):
    def __init__(self):
        self._data: dict[uuid.UUID, BankAccount] = {}

    def save(self, account: BankAccount) -> None:
        self._data[account.id] = account

    def get_by_id(self, account_id: uuid.UUID) -> Optional[BankAccount]:
        return self._data.get(account_id, None)

    def list_by_family(self, family_id: uuid.UUID) -> list[BankAccount]:
        return [acc for acc in self._data.values() if acc.family_id == family_id]


class CreditCardMemoryRepository(CreditCardRepository):
    """Nesse repositório falso, simulamos chaves estrangeiras duplas usando duas tabelas na memória. """
    def __init__(self):
        self._master_cards: dict[uuid.UUID, CreditCard] = {}
        self._instances: dict[uuid.UUID, CardInstance] = {}

    def save(self, credit_card: CreditCard) -> None:
        self._master_cards[credit_card.id] = credit_card

    def save_instance(self, card_instance: CardInstance) -> None:
        self._instances[card_instance.id] = card_instance

    def list_instances_by_family(self, family_id: uuid.UUID) -> list[CardInstance]:
        """Equivalente a um JOIN SQL na memória varrendo a família-mãe do contrato de crédito."""
        family_master_ids = [m.id for m in self._master_cards.values() if m.family_id == family_id]
        return [inst for inst in self._instances.values() if inst.credit_card_id in family_master_ids]


class TransactionMemoryRepository(TransactionRepository):
    def __init__(self):
        self._data: dict[uuid.UUID, Transaction] = {}
        
    def save(self, transaction: Transaction) -> None:
        self._data[transaction.id] = transaction

    def get_by_id(self, transaction_id: uuid.UUID) -> Optional[Transaction]:
        return self._data.get(transaction_id, None)

    def list_by_family(self, family_id: uuid.UUID) -> list[Transaction]:
        return [t for t in self._data.values() if t.family_id == family_id]

    def list_by_account(self, account_id: uuid.UUID) -> list[Transaction]:
        return [t for t in self._data.values() if t.bank_account_id == account_id]
        
    def list_by_credit_card_instance(self, card_instance_id: uuid.UUID) -> list[Transaction]:
        return [t for t in self._data.values() if t.card_instance_id == card_instance_id]


class CreditCardBillMemoryRepository(CreditCardBillRepository):
    def __init__(self):
        self._data: dict[uuid.UUID, CreditCardBill] = {}

    def save(self, bill: CreditCardBill) -> None:
        self._data[bill.id] = bill

    def get_by_id(self, bill_id: uuid.UUID) -> Optional[CreditCardBill]:
        return self._data.get(bill_id)

    def get_by_card_and_month(self, card_id: uuid.UUID, reference_month: str) -> Optional[CreditCardBill]:
        for b in self._data.values():
            if b.credit_card_id == card_id and b.reference_month == reference_month:
                return b
        return None
