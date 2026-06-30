from dataclasses import dataclass
from decimal import Decimal
import uuid
import pytest
from domain.financial.entities import Account, AccountType

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
