import pytest
import uuid

from application.dtos.family_dtos import CreateFamilyCostCenterDTO, UpdateFamilyCostCenterDTO
from application.services.family_cost_center_service import FamilyCostCenterService
from domain.family.entities import FamilyCostCenter
from domain.shared.exceptions import EntityAlreadyExistsError, EntityNotFoundError
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

    with pytest.raises(EntityAlreadyExistsError):
        service.create_family_cost_center(
            CreateFamilyCostCenterDTO(family_id=family_id, name="Casa de Praia")
        )

def test_create_family_cost_center_with_duplicate_name_ignoring_case_raises(
    service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id
):
    uow.family_cost_centers.save(FamilyCostCenter(family_id=family_id, name="Casa de Praia"))

    with pytest.raises(EntityAlreadyExistsError):
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
    with pytest.raises(EntityNotFoundError):
        service.get_family_cost_center(uuid.uuid4())

def test_list_family_cost_centers_by_family(
    service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id, other_family_id
):
    uow.family_cost_centers.save(FamilyCostCenter(family_id=family_id, name="Casa de Praia"))
    uow.family_cost_centers.save(FamilyCostCenter(family_id=family_id, name="Filhos"))
    uow.family_cost_centers.save(FamilyCostCenter(family_id=other_family_id, name="Outro"))

    responses = service.list_family_cost_centers(family_id)
    assert len(responses) == 2

def test_list_all_family_cost_centers_across_families(
    service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id, other_family_id
):
    uow.family_cost_centers.save(FamilyCostCenter(family_id=family_id, name="Casa de Praia"))
    uow.family_cost_centers.save(FamilyCostCenter(family_id=other_family_id, name="Outro"))

    responses = service.list_all_family_cost_centers()
    assert {r.name for r in responses} == {"Casa de Praia", "Outro"}

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

    with pytest.raises(EntityAlreadyExistsError):
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
    with pytest.raises(EntityNotFoundError):
        service.update_family_cost_center(uuid.uuid4(), UpdateFamilyCostCenterDTO(name="Qualquer"))

def test_delete_family_cost_center_success(service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id):
    cost_center = FamilyCostCenter(family_id=family_id, name="A deletar")
    uow.family_cost_centers.save(cost_center)

    service.delete_family_cost_center(cost_center.id)
    assert uow.family_cost_centers.get_by_id(cost_center.id) is None
    assert uow.committed is True

def test_delete_family_cost_center_not_found(service: FamilyCostCenterService):
    with pytest.raises(EntityNotFoundError):
        service.delete_family_cost_center(uuid.uuid4())

def test_delete_family_cost_center_with_dependencies_raises_and_keeps_it(
    service: FamilyCostCenterService, uow: FakeUnitOfWork, family_id
):
    from domain.shared.exceptions import EntityHasDependenciesError

    cost_center = FamilyCostCenter(family_id=family_id, name="Usado em transações")
    uow.family_cost_centers.save(cost_center)
    uow.family_cost_centers.set_has_dependencies(True)

    with pytest.raises(EntityHasDependenciesError):
        service.delete_family_cost_center(cost_center.id)

    assert uow.family_cost_centers.get_by_id(cost_center.id) is not None


def test_preview_cost_center_deletion_without_dependencies(service, uow, family_id):
    cost_center = FamilyCostCenter(family_id=family_id, name="Praia")
    uow.family_cost_centers.save(cost_center)

    preview = service.preview_family_cost_center_deletion(cost_center.id)

    assert (preview.name, preview.blocked_reason) == ("Praia", None)

def test_preview_cost_center_deletion_with_dependencies_gives_the_reason(service, uow, family_id):
    from domain.family.exceptions import cost_center_has_dependencies

    cost_center = FamilyCostCenter(family_id=family_id, name="Praia")
    uow.family_cost_centers.save(cost_center)
    uow.family_cost_centers.set_has_dependencies(True)

    preview = service.preview_family_cost_center_deletion(cost_center.id)

    assert preview.name == "Praia"
    assert preview.blocked_reason == str(cost_center_has_dependencies(cost_center.id))

def test_preview_cost_center_deletion_not_found(service):
    from domain.shared.exceptions import EntityNotFoundError

    with pytest.raises(EntityNotFoundError):
        service.preview_family_cost_center_deletion(uuid.uuid4())


def test_cost_center_listings_are_ordered_by_name(service, uow, family_id):
    for name in ("Praia", "filhos", "Escola"):
        uow.family_cost_centers.save(FamilyCostCenter(family_id=family_id, name=name))

    assert [c.name for c in service.list_all_family_cost_centers()] == ["Escola", "filhos", "Praia"]
    assert [c.name for c in service.list_family_cost_centers(family_id)] == ["Escola", "filhos", "Praia"]
