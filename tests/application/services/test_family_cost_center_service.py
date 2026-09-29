import pytest
import uuid

from application.dtos.family_dtos import CreateFamilyCostCenterDTO, UpdateFamilyCostCenterDTO
from application.services.family_cost_center_service import FamilyCostCenterService
from domain.family.entities import FamilyCostCenter
from domain.family.exceptions import (
    FamilyCostCenterAlreadyExistsError,
    FamilyCostCenterNotFoundError,
)
from fakes.family_fakes import FakeUnitOfWork

@pytest.fixture
def uow():
    return FakeUnitOfWork()

@pytest.fixture
def service(uow):
    return FamilyCostCenterService(uow)

@pytest.fixture
def family_id():
    return uuid.uuid4()

@pytest.fixture
def other_family_id():
    return uuid.uuid4()

def test_create_family_cost_center(service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id):
    dto = CreateFamilyCostCenterDTO(family_id=family_id, name="Núcleo Sogra")
    response = service.create_family_cost_center(dto)

    assert response.family_id == family_id
    assert response.name == "Núcleo Sogra"
    assert response.description is None
    assert response.id is not None

    saved = uow.family_cost_centers.get_by_id(response.id)
    assert saved is not None
    assert saved.name == "Núcleo Sogra"
    assert uow.committed is True

def test_create_family_cost_center_with_duplicate_name_in_same_family_raises(
    service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id
):
    uow.family_cost_centers.save(FamilyCostCenter(family_id=family_id, name="Casa de Praia"))

    with pytest.raises(FamilyCostCenterAlreadyExistsError):
        service.create_family_cost_center(
            CreateFamilyCostCenterDTO(family_id=family_id, name="Casa de Praia")
        )

def test_create_family_cost_center_with_duplicate_name_ignoring_case_raises(
    service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id
):
    uow.family_cost_centers.save(FamilyCostCenter(family_id=family_id, name="Casa de Praia"))

    with pytest.raises(FamilyCostCenterAlreadyExistsError):
        service.create_family_cost_center(
            CreateFamilyCostCenterDTO(family_id=family_id, name="casa de praia")
        )

def test_create_family_cost_center_with_same_name_in_different_family_is_allowed(
    service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id, other_family_id
):
    uow.family_cost_centers.save(FamilyCostCenter(family_id=other_family_id, name="Casa de Praia"))

    response = service.create_family_cost_center(
        CreateFamilyCostCenterDTO(family_id=family_id, name="Casa de Praia")
    )
    assert response.name == "Casa de Praia"
    assert response.family_id == family_id

def test_get_family_cost_center(service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id):
    cost_center = FamilyCostCenter(family_id=family_id, name="Filhos")
    uow.family_cost_centers.save(cost_center)

    response = service.get_family_cost_center(cost_center.id)
    assert response.id == cost_center.id
    assert response.name == "Filhos"

def test_get_family_cost_center_not_found(service: FamilyCostCenterService):
    with pytest.raises(FamilyCostCenterNotFoundError):
        service.get_family_cost_center(uuid.uuid4())

def test_list_family_cost_centers_by_family(
    service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id, other_family_id
):
    uow.family_cost_centers.save(FamilyCostCenter(family_id=family_id, name="Casa de Praia"))
    uow.family_cost_centers.save(FamilyCostCenter(family_id=family_id, name="Filhos"))
    uow.family_cost_centers.save(FamilyCostCenter(family_id=other_family_id, name="Outro"))

    responses = service.list_family_cost_centers(family_id)
    assert len(responses) == 2
    assert {r.name for r in responses} == {"Casa de Praia", "Filhos"}

def test_update_family_cost_center(service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id):
    cost_center = FamilyCostCenter(family_id=family_id, name="Nome Antigo")
    uow.family_cost_centers.save(cost_center)

    response = service.update_family_cost_center(
        cost_center.id, UpdateFamilyCostCenterDTO(name="Nome Novo", description="Atualizado")
    )

    assert response.name == "Nome Novo"
    assert response.description == "Atualizado"
    assert uow.committed is True

def test_update_family_cost_center_to_duplicate_name_in_same_family_raises(
    service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id
):
    uow.family_cost_centers.save(FamilyCostCenter(family_id=family_id, name="Casa de Praia"))
    other = FamilyCostCenter(family_id=family_id, name="Filhos")
    uow.family_cost_centers.save(other)

    with pytest.raises(FamilyCostCenterAlreadyExistsError):
        service.update_family_cost_center(other.id, UpdateFamilyCostCenterDTO(name="Casa de Praia"))

def test_update_family_cost_center_to_same_name_in_different_family_is_allowed(
    service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id, other_family_id
):
    uow.family_cost_centers.save(FamilyCostCenter(family_id=other_family_id, name="Casa de Praia"))
    mine = FamilyCostCenter(family_id=family_id, name="Filhos")
    uow.family_cost_centers.save(mine)

    response = service.update_family_cost_center(mine.id, UpdateFamilyCostCenterDTO(name="Casa de Praia"))
    assert response.name == "Casa de Praia"

def test_update_family_cost_center_not_found(service: FamilyCostCenterService):
    with pytest.raises(FamilyCostCenterNotFoundError):
        service.update_family_cost_center(uuid.uuid4(), UpdateFamilyCostCenterDTO(name="Qualquer"))

def test_delete_family_cost_center_success(service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id):
    cost_center = FamilyCostCenter(family_id=family_id, name="A deletar")
    uow.family_cost_centers.save(cost_center)

    service.delete_family_cost_center(cost_center.id)
    assert uow.family_cost_centers.get_by_id(cost_center.id) is None
    assert uow.committed is True

def test_delete_family_cost_center_not_found(service: FamilyCostCenterService):
    with pytest.raises(FamilyCostCenterNotFoundError):
        service.delete_family_cost_center(uuid.uuid4())
