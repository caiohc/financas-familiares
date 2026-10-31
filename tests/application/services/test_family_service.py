import pytest
import uuid
from decimal import Decimal
from typing import Optional

from application.dtos.family_dtos import CreateFamilyDTO, UpdateFamilyDTO
from application.services.family_service import FamilyService
from domain.family.entities import Family
from domain.shared.exceptions import EntityAlreadyExistsError
from fakes.family_fakes import FakeUnitOfWork

@pytest.fixture
def uow():
    return FakeUnitOfWork()

@pytest.fixture
def service(uow):
    return FamilyService(uow)

def test_create_family(service: FamilyService, uow: FakeUnitOfWork):
    dto = CreateFamilyDTO(name="Família Silva")
    response = service.create_family(dto)
    
    assert response.name == "Família Silva"
    assert response.current_balance == Decimal("0.0")
    assert response.id is not None
    
    # Verifica se foi salvo no repo e comitado
    saved = uow.families.get_by_id(response.id)
    assert saved is not None
    assert saved.name == "Família Silva"
    assert uow.committed is True

def test_create_family_allows_same_name_as_another_family(service: FamilyService, uow: FakeUnitOfWork):
    first = service.create_family(CreateFamilyDTO(name="Família Silva"))
    second = service.create_family(CreateFamilyDTO(name="família silva"))

    assert first.id != second.id
    assert len(uow.families.list_all()) == 2

def test_update_family_allows_name_of_another_family(service: FamilyService, uow: FakeUnitOfWork):
    uow.families.save(Family(name="Família Silva"))
    other = Family(name="Família Souza")
    uow.families.save(other)

    response = service.update_family(other.id, UpdateFamilyDTO(name="Família Silva"))

    assert response.name == "Família Silva"

def test_get_family(service: FamilyService, uow: FakeUnitOfWork):
    family = Family(name="Família Souza")
    uow.families.save(family)
    
    response = service.get_family(family.id)
    assert response.id == family.id
    assert response.name == "Família Souza"

def test_get_family_not_found(service: FamilyService):
    with pytest.raises(ValueError, match="não encontrada"):
        service.get_family(uuid.uuid4())

def test_list_families(service: FamilyService, uow: FakeUnitOfWork):
    uow.families.save(Family(name="Família 1"))
    uow.families.save(Family(name="Família 2"))
    
    responses = service.list_families()
    assert len(responses) == 2

def test_update_family(service: FamilyService, uow: FakeUnitOfWork):
    family = Family(name="Nome Antigo")
    uow.families.save(family)
    
    dto = UpdateFamilyDTO(name="Nome Novo")
    response = service.update_family(family.id, dto)
    
    assert response.name == "Nome Novo"
    assert uow.families.get_by_id(family.id).name == "Nome Novo"
    assert uow.committed is True

def test_update_family_to_own_current_name_is_allowed(service: FamilyService, uow: FakeUnitOfWork):
    family = Family(name="Família Silva")
    uow.families.save(family)

    response = service.update_family(family.id, UpdateFamilyDTO(name="Família Silva"))
    assert response.name == "Família Silva"

def test_update_family_not_found(service: FamilyService):
    with pytest.raises(ValueError, match="não encontrada"):
        service.update_family(uuid.uuid4(), UpdateFamilyDTO(name="Qualquer Nome"))

def test_delete_family_success(service: FamilyService, uow: FakeUnitOfWork):
    family = Family(name="Família a deletar")
    uow.families.save(family)
    
    service.delete_family(family.id)
    assert uow.families.get_by_id(family.id) is None
    assert uow.committed is True

def test_delete_family_with_dependencies(service: FamilyService, uow: FakeUnitOfWork):
    family = Family(name="Família Mãe")
    uow.families.save(family)
    uow.families.set_has_dependencies(True)

    with pytest.raises(ValueError, match="(?i)não é possível excluir a família pois existem dependências"):
        service.delete_family(family.id)

def test_delete_family_not_found(service: FamilyService):
    with pytest.raises(ValueError, match="não encontrada"):
        service.delete_family(uuid.uuid4())


def test_preview_family_deletion_without_dependencies(service, uow):
    family = Family(name="Silva")
    uow.families.save(family)

    preview = service.preview_family_deletion(family.id)

    assert (preview.name, preview.blocked_reason) == ("Silva", None)

def test_preview_family_deletion_with_dependencies_gives_the_reason(service, uow):
    from domain.family.exceptions import family_has_dependencies

    family = Family(name="Silva")
    uow.families.save(family)
    uow.families.set_has_dependencies(True)

    preview = service.preview_family_deletion(family.id)

    assert preview.name == "Silva"
    assert preview.blocked_reason == str(family_has_dependencies(family.id))

def test_preview_family_deletion_not_found(service):
    from domain.shared.exceptions import EntityNotFoundError

    with pytest.raises(EntityNotFoundError):
        service.preview_family_deletion(uuid.uuid4())


def test_list_families_is_ordered_by_name(service, uow):
    for name in ("Souza", "almeida", "Costa"):
        uow.families.save(Family(name=name))

    assert [f.name for f in service.list_families()] == ["almeida", "Costa", "Souza"]
