import uuid

from domain.financial.exceptions import category_already_exists, category_has_dependencies, category_not_found
from domain.shared.exceptions import EntityAlreadyExistsError, EntityHasDependenciesError, EntityNotFoundError

def test_category_already_exists():
    error = category_already_exists("Lazer")

    assert isinstance(error, EntityAlreadyExistsError)
    assert (error.entity, error.field, error.value) == ("Category", "name", "Lazer")
    assert str(error) == 'Já existe uma categoria com o nome "Lazer".'

def test_category_not_found():
    category_id = uuid.uuid4()
    error = category_not_found(category_id)

    assert isinstance(error, EntityNotFoundError)
    assert (error.entity, error.entity_id) == ("Category", category_id)
    assert str(error) == f"Categoria com ID {category_id} não encontrada."

def test_category_has_dependencies():
    category_id = uuid.uuid4()
    error = category_has_dependencies(category_id)

    assert isinstance(error, EntityHasDependenciesError)
    assert (error.entity, error.entity_id) == ("Category", category_id)
    assert str(error) == (
        "Não é possível excluir a categoria pois existem dependências vinculadas a ela (transações)."
    )
