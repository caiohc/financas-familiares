import uuid
from datetime import date
from domain.financial.entities import (
    Family, Member, Category, BankAccount, CreditCard, 
    CardInstance, Transaction, TransactionType
)

def test_family_and_member_creation():
    """Testa o elo financeiro mais básico: Famílias e Membros."""
    family = Family(name="Família Silva")
    member = Member(family_id=family.id, name="Caio Silva")
    
    assert family.id is not None
    assert member.id is not None
    assert member.family_id == family.id
    assert member.name == "Caio Silva"


def test_transaction_creation():
    """Garante que a transação armazene tipos de Enum corretamente."""
    transacao = Transaction(
        family_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        type=TransactionType.EXPENSE,
        date=date.today(),
        amount=150.50,
        description="Supermercado Fictício"
    )
    
    assert transacao.amount == 150.50
    assert transacao.type == TransactionType.EXPENSE
    assert transacao.bank_account_id is None  # Não foi vinculada a conta, reflete Dinheiro à vista.

def test_credit_card_hierarchy():
    """Prova que a hierarquia do contrato Master de Crédito para a emissão dos plásticos funciona usando Membros diferentes."""
    family_id = uuid.uuid4()
    
    # Os membros
    padre_id = uuid.uuid4()
    filho_id = uuid.uuid4()
    
    # O cartão mãe, contrato em nome do pai
    master_card = CreditCard(
        family_id=family_id,
        holder_id=padre_id,
        name="Cartão Infinite",
        limit=10000.00
    )
    
    # O plástico com o nome do filho atrelado logicamente ao contrato mãe
    instance_filho = CardInstance(
        credit_card_id=master_card.id,
        holder_id=filho_id,
        nickname="Cartão da Mesada"
    )
    
    assert master_card.holder_id != instance_filho.holder_id
    assert instance_filho.credit_card_id == master_card.id
