from dataclasses import dataclass
from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import (
    Family, 
    Member,
    AccountType,
    Account, 
    BankAccount, 
    Wallet, 
    CreditCard, 
    Tab,
    CardInstance,
    CreditCardBill,
    Category,
    Transaction,
    Transfer,
    TransactionType
)

# =====================================================================
# Testes da Entidade: Family
# =====================================================================

def test_family_creation_success():

    family = Family(name="Silva")
    assert family.name == "Silva"
    assert family.current_balance == Decimal('0.00')
    assert isinstance(family.id, uuid.UUID)

def test_family_missing_name():

    with pytest.raises(ValueError, match="Nome da família.*é obrigatório"):
        Family(name=None)

    with pytest.raises(ValueError, match="Nome da família.*é obrigatório"):
        Family(name="")
        
    with pytest.raises(ValueError, match="Nome da família.*é obrigatório"):
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

def test_member_missing_name():

    fam_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="Nome do membro.*é obrigatório"):
        Member(family_id=fam_id, name=None)

    with pytest.raises(ValueError, match="Nome do membro.*é obrigatório"):
        Member(family_id=fam_id, name="")   

    with pytest.raises(ValueError, match="Nome do membro.*é obrigatório"):
        Member(family_id=fam_id, name="   ")   

def test_member_missing_family():

    with pytest.raises(ValueError, match="Membro.*deve pertencer a uma família.*"):
        Member(family_id=None, name="João")

# =====================================================================
# Testes da Entidade: Account
# =====================================================================

def test_account_creation_success():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    nickname = 'nickname'

    @dataclass(kw_only=True)
    class TestAccount(Account):

        def __post_init__(self):
            self.account_type = AccountType.ASSET
            super().__post_init__()

        def _validate_balance_invariants(self):
            pass

    acc = TestAccount(family_id=fam_id, holder_id=holder_id, nickname=nickname)
    
    assert isinstance(acc.id, uuid.UUID)
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == nickname
    assert acc.current_balance == Decimal('0.00')
    assert acc.account_type == AccountType.ASSET
    


def test_account_missing_family():

    fam_id = None
    holder_id = uuid.uuid4()
    nickname = 'nickname'

    @dataclass(kw_only=True)
    class TestAccount(Account):

        def __post_init__(self):
            self.account_type = AccountType.ASSET
            super().__post_init__()

        def _validate_balance_invariants(self):
            pass

    with pytest.raises(ValueError, match="Toda conta.*deve estar vinculada a uma família.*"):
        TestAccount(family_id=None, holder_id=holder_id, nickname="X")

def test_account_missing_holder():

    fam_id = uuid.uuid4()
    holder_id = None
    nickname = 'nickname'

    @dataclass(kw_only=True)
    class TestAccount(Account):

        def __post_init__(self):
            self.account_type = AccountType.ASSET
            super().__post_init__()

        def _validate_balance_invariants(self):
            pass

    with pytest.raises(ValueError, match="Toda conta.*deve ter um titular.*"):
        TestAccount(family_id=fam_id, holder_id=None, nickname="X")

def test_account_missing_nickname():
    
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()

    @dataclass(kw_only=True)
    class TestAccount(Account):

        def __post_init__(self):
            self.account_type = AccountType.ASSET
            super().__post_init__()

        def _validate_balance_invariants(self):
            pass
    
    with pytest.raises(ValueError, match="O apelido.*é obrigatório para uma conta.*"):
        TestAccount(family_id=fam_id, holder_id=holder_id, nickname=None)

    with pytest.raises(ValueError, match="O apelido.*é obrigatório para uma conta.*"):
        TestAccount(family_id=fam_id, holder_id=holder_id, nickname="")
    
    with pytest.raises(ValueError, match="O apelido.*é obrigatório para uma conta.*"):
        TestAccount(family_id=fam_id, holder_id=holder_id, nickname="  ")

# =====================================================================
# Testes da Entidade: BankAccount
# =====================================================================

def test_bank_account_creation_success():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = BankAccount(family_id=fam_id, holder_id=holder_id, nickname="Minha Conta", bank="Nubank", 
        agency='001', account_number='123456-7')
    assert isinstance(acc.id, uuid.UUID)
    assert acc.account_type == AccountType.ASSET
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == "Minha Conta"
    assert acc.bank == "Nubank"
    assert acc.current_balance == Decimal('0.00')
    assert acc.agency == "001"
    assert acc.account_number == "123456-7"


    acc = BankAccount(family_id=fam_id, holder_id=holder_id, nickname="Minha Conta", bank="Nubank")
    assert isinstance(acc.id, uuid.UUID)
    assert acc.account_type == AccountType.ASSET
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == "Minha Conta"
    assert acc.bank == "Nubank"
    assert acc.current_balance == Decimal('0.00')


def test_bank_account_missing_bank():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="O nome do banco.*é obrigatório para uma conta bancária.*"):
        BankAccount(family_id=fam_id, holder_id=holder_id, nickname="X", bank=None)

    with pytest.raises(ValueError, match="O nome do banco.*é obrigatório para uma conta bancária.*"):
        BankAccount(family_id=fam_id, holder_id=holder_id, nickname="X", bank="")    
    
    with pytest.raises(ValueError, match="O nome do banco.*é obrigatório para uma conta bancária.*"):
        BankAccount(family_id=fam_id, holder_id=holder_id, nickname="X", bank="   ")
    
# =====================================================================
# =====================================================================
# Testes da Entidade: Wallet
# =====================================================================

def test_wallet_creation_success():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = Wallet(family_id=fam_id, holder_id=holder_id, nickname="Carteira Físca")
    assert isinstance(acc.id, uuid.UUID)
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.account_type == AccountType.ASSET
    assert acc.current_balance == Decimal('0.00')
    
    
def test_wallet_prevents_negative_balance_on_creation():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="A conta de carteira em espécie.* não pode ter saldo negativo"):
        Wallet(family_id=fam_id, holder_id=holder_id, nickname="Carteira", current_balance=Decimal('-10.0'))

# =====================================================================
# Testes da Entidade: Tab
# =====================================================================

def test_tab_creation_success():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    acc = Tab(family_id=fam_id, holder_id=holder_id, nickname="Padaria do Zé")
    assert isinstance(acc.id, uuid.UUID)
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == "Padaria do Zé"
    assert acc.account_type == AccountType.LIABILITY


# =====================================================================
# Testes da Entidade: CreditCard
# =====================================================================

def test_credit_card_creation_success():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    bank_account_id=uuid.uuid4()

    acc = CreditCard(
        family_id=fam_id, holder_id=holder_id, nickname="VISA Gold do Pedro", 
        brand="VISA", limit=5000.0, due_day=10, issuer="Nubank", tier="Gold",
        bank_account_id=bank_account_id
    )

    assert isinstance(acc.id, uuid.UUID)
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == "VISA Gold do Pedro"
    assert acc.brand == "VISA"
    assert acc.limit == Decimal('5000.00')
    assert acc.due_day == 10
    assert acc.issuer == "Nubank"
    assert acc.tier == "Gold"
    assert acc.bank_account_id == bank_account_id
    assert acc.account_type == AccountType.LIABILITY

    
    acc = CreditCard(
        family_id=fam_id, holder_id=holder_id, nickname="VISA Gold do Pedro", 
        brand="VISA", limit=5000.0, due_day=10, tier="Gold",
        bank_account_id=bank_account_id
    )

    assert isinstance(acc.id, uuid.UUID)
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == "VISA Gold do Pedro"
    assert acc.brand == "VISA"
    assert acc.limit == Decimal('5000.00')
    assert acc.due_day == 10
    assert acc.issuer == None
    assert acc.tier == "Gold"
    assert acc.bank_account_id == bank_account_id
    assert acc.account_type == AccountType.LIABILITY
  # Cobertura do gancho pass

    acc = CreditCard(
        family_id=fam_id, holder_id=holder_id, nickname="VISA Gold do Pedro", 
        brand="VISA", limit=5000.0, due_day=10, tier="Gold", issuer="Nubank"
    )

    assert isinstance(acc.id, uuid.UUID)
    assert acc.family_id == fam_id
    assert acc.holder_id == holder_id
    assert acc.nickname == "VISA Gold do Pedro"
    assert acc.brand == "VISA"
    assert acc.limit == Decimal('5000.00')
    assert acc.due_day == 10
    assert acc.issuer == 'Nubank'
    assert acc.tier == "Gold"
    assert acc.bank_account_id == None
    assert acc.account_type == AccountType.LIABILITY
  # Cobertura do gancho pass

def test_credit_card_missing_brand():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="A bandeira.* do cartão de crédito.* deve ser informada"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="", limit=5000.0, due_day=10, issuer="Nubank"
        )

    with pytest.raises(ValueError, match="A bandeira.* do cartão de crédito.* deve ser informada"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand=None, limit=5000.0, due_day=10, issuer="Nubank"
        )

    with pytest.raises(ValueError, match="A bandeira.* do cartão de crédito.* deve ser informada"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="  ", limit=5000.0, due_day=10, issuer="Nubank"
        )

def test_credit_card_missing_bank_and_issuer():

    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="Um cartão de crédito.*deve ter uma conta bancária.* vinculada ou um emissor.*"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="Mastercard", limit=5000.0, due_day=10, issuer=None, bank_account_id=None
        )

    with pytest.raises(ValueError, match="Um cartão de crédito.*deve ter uma conta bancária.* vinculada ou um emissor.*"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="Mastercard", limit=5000.0, due_day=10, issuer="", bank_account_id=None
        )

    with pytest.raises(ValueError, match="Um cartão de crédito.*deve ter uma conta bancária.* vinculada ou um emissor.*"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="Mastercard", limit=5000.0, due_day=10, issuer="  ", bank_account_id=None
        )

def test_credit_card_invalid_due_day():
    fam_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="O dia de vencimento.*entre 1 e 31"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="Mastercard", limit=5000.0, due_day=0, issuer="Nubank"
        )

    with pytest.raises(ValueError, match="O dia de vencimento.*entre 1 e 31"):
        CreditCard(
            family_id=fam_id, holder_id=holder_id, nickname="Cartão Black", 
            brand="Mastercard", limit=5000.0, due_day=32, issuer="Nubank"
        )

# =====================================================================
# Testes da Entidade: CardInstance
# =====================================================================

def test_card_instance_creation_success():
    fam_id = uuid.uuid4()
    credit_card_id = uuid.uuid4()
    holder_id = uuid.uuid4()
    
    instance = CardInstance(
        family_id=fam_id,
        credit_card_id=credit_card_id,
        holder_id=holder_id,
        nickname="Cartão Virtual para Ifood"
    )
    
    assert isinstance(instance.id, uuid.UUID)
    assert instance.family_id == fam_id
    assert instance.credit_card_id == credit_card_id
    assert instance.holder_id == holder_id
    assert instance.nickname == "Cartão Virtual para Ifood"

# =====================================================================
# Testes da Entidade: Category
# =====================================================================

def test_category_creation_success():
    cat = Category(name="Alimentação", type=TransactionType.EXPENSE)
    assert isinstance(cat.id, uuid.UUID)
    assert cat.name == "Alimentação"
    assert cat.type == TransactionType.EXPENSE

def test_category_missing_name():
    with pytest.raises(ValueError, match="Nome da categoria.*é obrigatório"):
        Category(name=None, type=TransactionType.EXPENSE)
    
    with pytest.raises(ValueError, match="Nome da categoria.*é obrigatório"):
        Category(name="   ", type=TransactionType.EXPENSE)

def test_category_missing_type():
    with pytest.raises(ValueError, match="Tipo da categoria.*é obrigatório"):
        Category(name="Lazer", type=None)

# =====================================================================
# Testes do Agregado: Transfer
# =====================================================================

def test_transfer_creation_success():
    fam_id = uuid.uuid4()
    src_id = uuid.uuid4()
    dst_id = uuid.uuid4()
    from datetime import date
    
    transfer = Transfer(
        family_id=fam_id,
        source_account_id=src_id,
        destination_account_id=dst_id,
        amount=Decimal('150.50'),
        date=date.today(),
        description="Mesada"
    )
    
    assert isinstance(transfer.id, uuid.UUID)
    assert transfer.amount == Decimal('150.50')
    assert transfer.description == "Mesada"

def test_transfer_invalid_amount():
    fam_id = uuid.uuid4()
    src_id = uuid.uuid4()
    dst_id = uuid.uuid4()
    from datetime import date
    
    with pytest.raises(ValueError, match="O valor da transferência.*deve ser maior que zero"):
        Transfer(
            family_id=fam_id, source_account_id=src_id, destination_account_id=dst_id,
            amount=Decimal('0.0'), date=date.today()
        )
        
    with pytest.raises(ValueError, match="O valor da transferência.*deve ser maior que zero"):
        Transfer(
            family_id=fam_id, source_account_id=src_id, destination_account_id=dst_id,
            amount=Decimal('-50.0'), date=date.today()
        )

def test_transfer_same_account_error():
    fam_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    from datetime import date
    
    with pytest.raises(ValueError, match="A conta de origem e destino.*não podem ser a mesma"):
        Transfer(
            family_id=fam_id, source_account_id=acc_id, destination_account_id=acc_id,
            amount=Decimal('100.0'), date=date.today()
        )

def test_transfer_generate_transactions():
    fam_id = uuid.uuid4()
    src_id = uuid.uuid4()
    dst_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    from datetime import date
    
    transfer = Transfer(
        family_id=fam_id,
        source_account_id=src_id,
        destination_account_id=dst_id,
        amount=Decimal('200.0'),
        date=date.today(),
        description="Pagamento fatura"
    )
    
    out_tx, in_tx = transfer.generate_transactions(category_id=cat_id)
    
    assert out_tx.type == TransactionType.TRANSFER_OUT
    assert out_tx.account_id == src_id
    assert out_tx.amount == Decimal('200.0')
    assert out_tx.transfer_id == transfer.id
    assert out_tx.category_id == cat_id
    assert out_tx.is_forecast is False
    
    assert in_tx.type == TransactionType.TRANSFER_IN
    assert in_tx.account_id == dst_id
    assert in_tx.amount == Decimal('200.0')
    assert in_tx.transfer_id == transfer.id
    assert in_tx.category_id == cat_id
    assert in_tx.is_forecast is False

# =====================================================================
# Testes da Entidade: CardInstance
# =====================================================================

def test_card_instance_creation_success():
    fam_id = uuid.uuid4()
    card_id = uuid.uuid4()
    holder_id = uuid.uuid4()

    instance = CardInstance(
        family_id=fam_id,
        credit_card_id=card_id,
        holder_id=holder_id,
        nickname="Físico"
    )

    assert isinstance(instance.id, uuid.UUID)
    assert instance.family_id == fam_id
    assert instance.credit_card_id == card_id
    assert instance.holder_id == holder_id
    assert instance.nickname == "Físico"

def test_card_instance_validations():
    fam_id = uuid.uuid4()
    card_id = uuid.uuid4()
    holder_id = uuid.uuid4()

    with pytest.raises(ValueError, match="associado a uma família"):
        CardInstance(family_id=None, credit_card_id=card_id, holder_id=holder_id, nickname="Físico")

    with pytest.raises(ValueError, match="associado a um contrato de cartão"):
        CardInstance(family_id=fam_id, credit_card_id=None, holder_id=holder_id, nickname="Físico")

    with pytest.raises(ValueError, match="deve ter um portador"):
        CardInstance(family_id=fam_id, credit_card_id=card_id, holder_id=None, nickname="Físico")

# =====================================================================
# Testes da Entidade: CreditCardBill
# =====================================================================

def test_credit_card_bill_creation_success():
    fam_id = uuid.uuid4()
    card_id = uuid.uuid4()
    from datetime import date
    due = date(2026, 4, 10)

    bill = CreditCardBill(
        family_id=fam_id,
        credit_card_id=card_id,
        reference_month="2026-04",
        due_date=due
    )

    assert isinstance(bill.id, uuid.UUID)
    assert bill.family_id == fam_id
    assert bill.credit_card_id == card_id
    assert bill.reference_month == "2026-04"
    assert bill.due_date == due
    assert bill.total_amount == Decimal('0.00')
    assert bill.is_closed is False

def test_credit_card_bill_validations():
    fam_id = uuid.uuid4()
    card_id = uuid.uuid4()
    from datetime import date
    due = date(2026, 4, 10)

    with pytest.raises(ValueError, match="associada a uma família"):
        CreditCardBill(family_id=None, credit_card_id=card_id, reference_month="2026-04", due_date=due)

    with pytest.raises(ValueError, match="associada a um contrato de cartão"):
        CreditCardBill(family_id=fam_id, credit_card_id=None, reference_month="2026-04", due_date=due)

    with pytest.raises(ValueError, match="formato YYYY-MM"):
        CreditCardBill(family_id=fam_id, credit_card_id=card_id, reference_month="04-2026", due_date=due)

    with pytest.raises(ValueError, match="data de vencimento.*informada"):
        CreditCardBill(family_id=fam_id, credit_card_id=card_id, reference_month="2026-04", due_date=None)

# =====================================================================
# Testes da Entidade: Transaction
# =====================================================================

def test_transaction_creation_success():
    fam_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    from datetime import date
    
    tx = Transaction(
        family_id=fam_id,
        category_id=cat_id,
        account_id=uuid.uuid4(),
        type=TransactionType.EXPENSE,
        date=date.today(),
        amount=Decimal('50.00'),
        description="Supermercado"
    )

    assert tx.id is not None
    assert tx.account_id is not None
    assert tx.family_id == fam_id
    assert tx.category_id == cat_id
    assert tx.type == TransactionType.EXPENSE
    assert tx.date == date.today()
    assert tx.amount == Decimal('50.00')
    assert tx.description == "Supermercado"
    assert tx.is_forecast is False

def test_transaction_validations():
    fam_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    from datetime import date
    dt = date.today()

    with pytest.raises(ValueError, match="pertencer a uma família"):
        Transaction(family_id=None, category_id=cat_id, account_id=acc_id, type=TransactionType.EXPENSE, date=dt, amount=Decimal('10'), description="D")

    with pytest.raises(ValueError, match="ter uma categoria"):
        Transaction(family_id=fam_id, category_id=None, account_id=acc_id, type=TransactionType.EXPENSE, date=dt, amount=Decimal('10'), description="D")

    with pytest.raises(ValueError, match="ter um tipo"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=acc_id, type=None, date=dt, amount=Decimal('10'), description="D")

    with pytest.raises(ValueError, match="ter uma data"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=acc_id, type=TransactionType.EXPENSE, date=None, amount=Decimal('10'), description="D")

    with pytest.raises(ValueError, match="ter um valor"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=acc_id, type=TransactionType.EXPENSE, date=dt, amount=None, description="D")

    with pytest.raises(ValueError, match="ter uma descrição"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=acc_id, type=TransactionType.EXPENSE, date=dt, amount=Decimal('10'), description="")

    with pytest.raises(ValueError, match="informar se é uma previsão"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=acc_id, type=TransactionType.EXPENSE, date=dt, amount=Decimal('10'), description="D", is_forecast="False")

    with pytest.raises(ValueError, match="associada a uma conta"):
        Transaction(family_id=fam_id, category_id=cat_id, account_id=None, type=TransactionType.EXPENSE, date=dt, amount=Decimal('10'), description="D")