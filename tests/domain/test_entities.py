import uuid
import pytest
from domain.financial.entities import (
    Family, 
    Member, 
    AccountType, 
    BankAccount, 
    CashAccount, 
    CreditCard, 
    TabAccount
)

# =====================================================================
# Testes da Entidade: Family
# =====================================================================
def test_family_creation_success():
    family = Family(name="Silva")
    assert family.name == "Silva"
    assert family.current_balance == 0.0
    assert isinstance(family.id, uuid.UUID)

def test_family_requires_name():
    with pytest.raises(ValueError, match="Nome da família é obrigatório"):
        Family(name="")
        
    with pytest.raises(ValueError, match="Nome da família é obrigatório"):
        Family(name="   ")

# =====================================================================
# Testes da Entidade: Member
# =====================================================================
def test_member_creation_success():
    fam_id = uuid.uuid4()
    member = Member(family_id=fam_id, name="João")
    assert member.name == "João"
    assert member.family_id == fam_id
    assert isinstance(member.id, uuid.UUID)

def test_member_requires_name():
    fam_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Nome do membro é obrigatório"):
        Member(family_id=fam_id, name="")

def test_member_requires_family():
    with pytest.raises(ValueError, match="Membro deve pertencer a uma família"):
        Member(family_id=None, name="João")

# =====================================================================
# Testes da Entidade: BankAccount
# =====================================================================
def test_bank_account_creation_success():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = BankAccount(family_id=fam_id, holder_id=holder_id, nickname="Minha Conta", bank="Nubank")
    assert acc.account_type == AccountType.ASSET
    assert acc.bank == "Nubank"

def test_bank_account_invariants_family_and_holder():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()

    # Falta família
    with pytest.raises(ValueError, match="Toda conta deve estar vinculada a uma família"):
        BankAccount(family_id=None, holder_id=holder_id, nickname="X", bank="Nubank")
        
    # Falta titular
    with pytest.raises(ValueError, match="Toda conta deve ter um titular"):
        BankAccount(family_id=fam_id, holder_id=None, nickname="X", bank="Nubank")

def test_bank_account_requires_bank_name():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    # Falta nome do banco
    with pytest.raises(ValueError, match="nome do banco .* obrigatório"):
        BankAccount(family_id=fam_id, holder_id=holder_id, nickname="X", bank="   ")

def test_bank_account_factory_nickname_generation():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    # 1. Quando o nickname é explicitamente fornecido
    acc = BankAccount.create(
        family_id=fam_id, holder_id=holder_id, holder_name="Maria da Silva",
        bank="Itaú", nickname="Conta Conjunta"
    )
    assert acc.nickname == "Conta Conjunta"

    # 2. Quando o nickname não é fornecido (Geração Dinâmica)
    acc2 = BankAccount.create(
        family_id=fam_id, holder_id=holder_id, holder_name="Eudésio Penaforte Bradeiro",
        bank="Itaú", nickname=None
    )
    assert acc2.nickname == "Itaú (Eudésio)", "O nickname deveria ser 'Itaú (Eudésio)'"

    # 3. Quando o nickname não é fornecido e o holder_name é vazio
    acc3 = BankAccount.create(
        family_id=fam_id, holder_id=holder_id, holder_name="",
        bank="Bradesco", nickname=None
    )
    assert acc3.nickname == "Bradesco", "O nickname deveria ser apenas o nome do banco"

# =====================================================================
# Testes da Entidade: CashAccount
# =====================================================================
def test_cash_account_creation_success():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = CashAccount(family_id=fam_id, holder_id=holder_id, nickname="Carteira Físca")
    assert acc.account_type == AccountType.ASSET
    assert acc.current_balance == 0.0
    
def test_cash_account_prevents_negative_balance_on_creation():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="A conta de dinheiro em espécie não pode ter saldo negativo"):
        CashAccount(family_id=fam_id, holder_id=holder_id, nickname="Carteira", current_balance=-10.0)

# =====================================================================
# Testes das Demais Entidades (Passivos)
# =====================================================================
def test_credit_card_creation_success():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = CreditCard(
        family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
        brand="Mastercard", limit=5000.0, due_day=10
    )
    assert acc.account_type == AccountType.LIABILITY

def test_tab_account_creation_success():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = TabAccount(family_id=fam_id, holder_id=holder_id, nickname="Padaria do Zé")
    assert acc.account_type == AccountType.LIABILITY
