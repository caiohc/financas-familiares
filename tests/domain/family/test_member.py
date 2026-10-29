import uuid
import pytest
from domain.shared.exceptions import DomainValidationError
from domain.family.entities import Member

def test_member_creation_success():

    fam_id = uuid.uuid4()
    member = Member(family_id=fam_id, name="João")
    assert member.name == "João"
    assert member.family_id == fam_id
    assert isinstance(member.id, uuid.UUID)

@pytest.mark.parametrize("blank_name", [None, "", "   "])
def test_member_missing_name(blank_name):
    with pytest.raises(DomainValidationError, match="Nome do membro.* é obrigatório"):
        Member(family_id=uuid.uuid4(), name=blank_name)

def test_member_missing_family():

    with pytest.raises(DomainValidationError, match="Membro.* deve pertencer a uma família.*"):
        Member(family_id=None, name="João")

def test_member_name_is_stripped_on_creation():
    member = Member(family_id=uuid.uuid4(), name="  João  ")
    assert member.name == "João"

def test_member_rename():
    member = Member(family_id=uuid.uuid4(), name="João")
    member.rename("Maria")
    assert member.name == "Maria"

def test_member_rename_strips_name():
    member = Member(family_id=uuid.uuid4(), name="João")
    member.rename("  Maria  ")
    assert member.name == "Maria"

@pytest.mark.parametrize("blank_name", [None, "", "   "])
def test_member_rename_to_blank_raises_and_keeps_current_name(blank_name):
    member = Member(family_id=uuid.uuid4(), name="João")

    with pytest.raises(DomainValidationError, match="Nome do membro.* é obrigatório"):
        member.rename(blank_name)

    assert member.name == "João"

def test_member_validation_errors_report_the_field():
    with pytest.raises(DomainValidationError) as name_error:
        Member(family_id=uuid.uuid4(), name="   ")
    assert name_error.value.field == "name"

    with pytest.raises(DomainValidationError) as family_error:
        Member(family_id=None, name="João")
    assert family_error.value.field == "family_id"
