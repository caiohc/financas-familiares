import uuid

import pytest

from application.dtos.family_dtos import CreateMemberDTO, UpdateMemberDTO
from application.services.member_service import MemberService
from domain.family.entities import Member
from domain.shared.exceptions import (
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)
from fakes.family_fakes import FakeUnitOfWork

@pytest.fixture
def uow():
    return FakeUnitOfWork()

@pytest.fixture
def service(uow):
    return MemberService(uow)

@pytest.fixture
def family_id():
    return uuid.uuid4()

@pytest.fixture
def other_family_id():
    return uuid.uuid4()

def test_create_member(service: MemberService, uow: FakeUnitOfWork, family_id):
    response = service.create_member(CreateMemberDTO(family_id=family_id, name="João"))

    assert response.family_id == family_id
    assert response.name == "João"
    assert uow.members.get_by_id(response.id) is not None
    assert uow.committed is True

def test_create_member_with_duplicate_name_in_same_family_raises(
    service: MemberService, uow: FakeUnitOfWork, family_id
):
    uow.members.save(Member(family_id=family_id, name="João"))

    with pytest.raises(EntityAlreadyExistsError):
        service.create_member(CreateMemberDTO(family_id=family_id, name="joão"))

def test_create_member_with_padded_duplicate_name_raises(service: MemberService, uow: FakeUnitOfWork, family_id):
    uow.members.save(Member(family_id=family_id, name="João"))

    with pytest.raises(EntityAlreadyExistsError):
        service.create_member(CreateMemberDTO(family_id=family_id, name="  João  "))

def test_create_member_with_same_name_in_different_family_is_allowed(
    service: MemberService, uow: FakeUnitOfWork, family_id, other_family_id
):
    uow.members.save(Member(family_id=other_family_id, name="João"))

    response = service.create_member(CreateMemberDTO(family_id=family_id, name="João"))
    assert response.family_id == family_id

def test_create_member_with_blank_name_raises_validation_error(service: MemberService, family_id):
    with pytest.raises(DomainValidationError):
        service.create_member(CreateMemberDTO(family_id=family_id, name="   "))

def test_get_member(service: MemberService, uow: FakeUnitOfWork, family_id):
    member = Member(family_id=family_id, name="Maria")
    uow.members.save(member)

    response = service.get_member(member.id)
    assert (response.id, response.name) == (member.id, "Maria")

def test_get_member_not_found(service: MemberService):
    with pytest.raises(EntityNotFoundError):
        service.get_member(uuid.uuid4())

def test_list_family_members(service: MemberService, uow: FakeUnitOfWork, family_id, other_family_id):
    uow.members.save(Member(family_id=family_id, name="João"))
    uow.members.save(Member(family_id=family_id, name="Maria"))
    uow.members.save(Member(family_id=other_family_id, name="Pedro"))

    assert {r.name for r in service.list_family_members(family_id)} == {"João", "Maria"}

def test_list_all_members_across_families(service: MemberService, uow: FakeUnitOfWork, family_id, other_family_id):
    uow.members.save(Member(family_id=family_id, name="João"))
    uow.members.save(Member(family_id=other_family_id, name="Pedro"))

    assert {r.name for r in service.list_all_members()} == {"João", "Pedro"}

def test_update_member(service: MemberService, uow: FakeUnitOfWork, family_id):
    member = Member(family_id=family_id, name="Nome Antigo")
    uow.members.save(member)

    response = service.update_member(member.id, UpdateMemberDTO(name="Nome Novo"))

    assert response.name == "Nome Novo"
    assert uow.committed is True

def test_update_member_to_own_current_name_is_allowed(service: MemberService, uow: FakeUnitOfWork, family_id):
    member = Member(family_id=family_id, name="João")
    uow.members.save(member)

    assert service.update_member(member.id, UpdateMemberDTO(name="João")).name == "João"

def test_update_member_to_duplicate_name_in_same_family_raises(service: MemberService, uow: FakeUnitOfWork, family_id):
    uow.members.save(Member(family_id=family_id, name="João"))
    other = Member(family_id=family_id, name="Maria")
    uow.members.save(other)

    with pytest.raises(EntityAlreadyExistsError):
        service.update_member(other.id, UpdateMemberDTO(name="joão"))

def test_update_member_to_blank_name_raises_and_keeps_current_name(
    service: MemberService, uow: FakeUnitOfWork, family_id
):
    member = Member(family_id=family_id, name="João")
    uow.members.save(member)

    with pytest.raises(DomainValidationError):
        service.update_member(member.id, UpdateMemberDTO(name="   "))

    assert uow.members.get_by_id(member.id).name == "João"

def test_update_member_not_found(service: MemberService):
    with pytest.raises(EntityNotFoundError):
        service.update_member(uuid.uuid4(), UpdateMemberDTO(name="Qualquer"))

def test_delete_member_success(service: MemberService, uow: FakeUnitOfWork, family_id):
    member = Member(family_id=family_id, name="A excluir")
    uow.members.save(member)

    service.delete_member(member.id)

    assert uow.members.get_by_id(member.id) is None
    assert uow.committed is True

def test_delete_member_with_dependencies_raises_and_keeps_member(
    service: MemberService, uow: FakeUnitOfWork, family_id
):
    member = Member(family_id=family_id, name="Titular")
    uow.members.save(member)
    uow.members.set_has_dependencies(True)

    with pytest.raises(EntityHasDependenciesError):
        service.delete_member(member.id)

    assert uow.members.get_by_id(member.id) is not None

def test_delete_member_not_found(service: MemberService):
    with pytest.raises(EntityNotFoundError):
        service.delete_member(uuid.uuid4())


def test_preview_member_deletion_without_dependencies(service, uow, family_id):
    member = Member(family_id=family_id, name="João")
    uow.members.save(member)

    preview = service.preview_member_deletion(member.id)

    assert (preview.name, preview.blocked_reason) == ("João", None)

def test_preview_member_deletion_with_dependencies_gives_the_reason(service, uow, family_id):
    from domain.family.exceptions import member_has_dependencies

    member = Member(family_id=family_id, name="João")
    uow.members.save(member)
    uow.members.set_has_dependencies(True)

    preview = service.preview_member_deletion(member.id)

    assert preview.name == "João"
    assert preview.blocked_reason == str(member_has_dependencies(member.id))

def test_preview_member_deletion_not_found(service):
    from domain.shared.exceptions import EntityNotFoundError

    with pytest.raises(EntityNotFoundError):
        service.preview_member_deletion(uuid.uuid4())


def test_member_listings_are_ordered_by_name(service, uow, family_id):
    for name in ("Pedro", "ana", "João"):
        uow.members.save(Member(family_id=family_id, name=name))

    assert [m.name for m in service.list_all_members()] == ["ana", "João", "Pedro"]
    assert [m.name for m in service.list_family_members(family_id)] == ["ana", "João", "Pedro"]
