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
    acc._validate_balance_invariants()
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

def test_cash_account_factory_nickname_generation():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    # 1. Quando o nickname é explicitamente fornecido
    acc = CashAccount.create(
        family_id=fam_id, holder_id=holder_id, holder_name="Maria da Silva",
        nickname="Cofre"
    )
    assert acc.nickname == "Cofre"

    # 2. Quando o nickname não é fornecido (Geração Dinâmica)
    acc2 = CashAccount.create(
        family_id=fam_id, holder_id=holder_id, holder_name="Caio Silva",
        nickname=None
    )
    assert acc2.nickname == "Espécie (Caio)"

    # 3. Quando o nickname não é fornecido e o holder_name é vazio
    acc3 = CashAccount.create(
        family_id=fam_id, holder_id=holder_id, holder_name="",
        nickname=None
    )
    assert acc3.nickname == "Espécie"

# =====================================================================
# Testes das Demais Entidades (Passivos)
# =====================================================================
def test_credit_card_creation_success():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = CreditCard(
        family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
        brand="Mastercard", limit=5000.0, due_day=10, issuer="Nubank"
    )
    assert acc.account_type == AccountType.LIABILITY
    acc._validate_balance_invariants()  # Cobertura do gancho pass

def test_credit_card_missing_brand():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="A bandeira do cartão de crédito deve ser informada"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="", limit=5000.0, due_day=10, issuer="Nubank"
        )

def test_credit_card_missing_bank_and_issuer():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="Um cartão de crédito deve ter uma conta bancária vinculada ou um emissor"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="Mastercard", limit=5000.0, due_day=10, issuer=None, bank_account_id=None
        )

def test_credit_card_factory_nickname_and_issuer():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    bank_account_id = uuid.uuid4()
    # Simulando o Serviço de Aplicação:
    # O Serviço sabe o nickname da BankAccount associada: "Bradesco (Caio)"
    issuer_do_banco = "Bradesco (Caio)"

    # 1. BankAccount associada, tier preenchido
    # O Serviço passa o issuer_do_banco
    cc1 = CreditCard.create(
        family_id=fam_id, holder_id=holder_id, brand="VISA", tier="Black", 
        limit=1000, due_day=5, bank_account_id=bank_account_id, issuer=issuer_do_banco
    )
    assert cc1.nickname == "Bradesco (Caio) - VISA Black"

    # 2. BankAccount associada, sem tier
    cc2 = CreditCard.create(
        family_id=fam_id, holder_id=holder_id, brand="Mastercard", tier="", 
        limit=1000, due_day=5, bank_account_id=bank_account_id, issuer=issuer_do_banco
    )
    assert cc2.nickname == "Bradesco (Caio) - Mastercard"

    # 3. Sem BankAccount, mas passando um issuer explicitamente 
    # (pois o Domínio exige bank_account_id ou issuer)
    cc3 = CreditCard.create(
        family_id=fam_id, holder_id=holder_id, brand="Elo", 
        limit=1000, due_day=5, issuer="Caixa"
    )
    assert cc3.issuer == "Caixa"
    assert cc3.nickname == "Caixa - Elo"

    # 4. Nickname e issuer fornecidos explicitamente
    cc4 = CreditCard.create(
        family_id=fam_id, holder_id=holder_id, brand="VISA", tier="Platinum", 
        limit=1000, due_day=5, issuer="Meu Banco Falso", nickname="Meu Cartão Customizado",
        bank_account_id=bank_account_id
    )
    assert cc4.issuer == "Meu Banco Falso"
    assert cc4.nickname == "Meu Cartão Customizado"
    
    # 5. Fallback com bank_account_nickname (passando o ID para não ferir invariante)
    cc5 = CreditCard.create(
        family_id=fam_id, holder_id=holder_id, brand="AMEX", tier="Green", 
        limit=1000, due_day=5, bank_account_nickname="Itaú (Caio)", issuer=None,
        bank_account_id=bank_account_id
    )
    assert cc5.nickname == "Itaú (Caio) - AMEX Green"

    # 6. Sem issuer, sem bank_account_nickname, mas com bank_account_id (cobertura do else final)
    cc6 = CreditCard.create(
        family_id=fam_id, holder_id=holder_id, brand="Nubank", tier="Gold",
        limit=1000, due_day=5, bank_account_id=bank_account_id
    )
    assert cc6.nickname == "Nubank Gold"

def test_tab_account_creation_success():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = TabAccount(family_id=fam_id, holder_id=holder_id, nickname="Padaria do Zé")
    assert acc.account_type == AccountType.LIABILITY
    acc._validate_balance_invariants()

def test_tab_account_factory_nickname_generation():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    # 1. Quando o nickname é explicitamente fornecido
    acc = TabAccount.create(
        family_id=fam_id, holder_id=holder_id, holder_name="Maria da Silva",
        nickname="Mercantil"
    )
    assert acc.nickname == "Mercantil"

    # 2. Quando o nickname não é fornecido (Geração Dinâmica)
    acc2 = TabAccount.create(
        family_id=fam_id, holder_id=holder_id, holder_name="Caio Silva",
        nickname=None
    )
    assert acc2.nickname == "Fiado (Caio)"

    # 3. Quando o nickname não é fornecido e o holder_name é vazio
    acc3 = TabAccount.create(
        family_id=fam_id, holder_id=holder_id, holder_name="",
        nickname=None
    )
    assert acc3.nickname == "Fiado"
