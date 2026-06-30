import uuid
import pytest
from domain.financial.entities import Member

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
