import uuid

from domain.family.exceptions import (
    cost_center_already_exists,
    cost_center_has_dependencies,
    cost_center_not_found,
    family_already_exists,
    family_has_dependencies,
    family_not_found,
    member_already_exists,
    member_has_dependencies,
    member_not_found,
)
from domain.shared.exceptions import (
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)

def test_family_already_exists():
    error = family_already_exists("Silva")

    assert isinstance(error, EntityAlreadyExistsError)
    assert (error.entity, error.field, error.value) == ("Family", "name", "Silva")
    assert str(error) == 'Já existe uma família com o nome "Silva".'

def test_family_not_found():
    family_id = uuid.uuid4()
    error = family_not_found(family_id)

    assert isinstance(error, EntityNotFoundError)
    assert (error.entity, error.entity_id) == ("Family", family_id)
    assert str(error) == f"Família com ID {family_id} não encontrada."

def test_family_has_dependencies():
    family_id = uuid.uuid4()
    error = family_has_dependencies(family_id)

    assert isinstance(error, EntityHasDependenciesError)
    assert (error.entity, error.entity_id) == ("Family", family_id)
    assert str(error) == (
        "Não é possível excluir a família pois existem dependências vinculadas a ela "
        "(membros, centros de custo, contas ou transações)."
    )

def test_cost_center_already_exists():
    error = cost_center_already_exists("Casa de Praia")

    assert isinstance(error, EntityAlreadyExistsError)
    assert (error.entity, error.field, error.value) == ("FamilyCostCenter", "name", "Casa de Praia")
    assert str(error) == 'Já existe um centro de custo com o nome "Casa de Praia" nesta família.'

def test_cost_center_not_found():
    cost_center_id = uuid.uuid4()
    error = cost_center_not_found(cost_center_id)

    assert isinstance(error, EntityNotFoundError)
    assert (error.entity, error.entity_id) == ("FamilyCostCenter", cost_center_id)
    # Concordância de gênero: "encontrado" (centro de custo), não "encontrada" (família).
    assert str(error) == f"Centro de custo com ID {cost_center_id} não encontrado."

def test_cost_center_has_dependencies():
    cost_center_id = uuid.uuid4()
    error = cost_center_has_dependencies(cost_center_id)

    assert isinstance(error, EntityHasDependenciesError)
    assert (error.entity, error.entity_id) == ("FamilyCostCenter", cost_center_id)
    assert str(error) == (
        "Não é possível excluir o centro de custo pois existem dependências vinculadas a ele (transações)."
    )

def test_member_already_exists():
    error = member_already_exists("João")

    assert isinstance(error, EntityAlreadyExistsError)
    assert (error.entity, error.field, error.value) == ("Member", "name", "João")
    assert str(error) == 'Já existe um membro com o nome "João" nesta família.'

def test_member_not_found():
    member_id = uuid.uuid4()
    error = member_not_found(member_id)

    assert isinstance(error, EntityNotFoundError)
    assert (error.entity, error.entity_id) == ("Member", member_id)
    assert str(error) == f"Membro com ID {member_id} não encontrado."

def test_member_has_dependencies():
    member_id = uuid.uuid4()
    error = member_has_dependencies(member_id)

    assert isinstance(error, EntityHasDependenciesError)
    assert (error.entity, error.entity_id) == ("Member", member_id)
    assert str(error) == (
        "Não é possível excluir o membro pois existem dependências vinculadas a ele (contas ou cartões)."
    )
