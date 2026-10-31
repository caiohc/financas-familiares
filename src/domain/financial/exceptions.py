"""
Mensagens das exceções do domínio financeiro.

Não são classes novas: cada função devolve uma das exceções compartilhadas de
domain/shared/exceptions.py com a mensagem do caso.
"""
from domain.shared.exceptions import (
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)


def category_already_exists(name: str) -> EntityAlreadyExistsError:
    return EntityAlreadyExistsError("Category", "name", name, f"Já existe uma categoria com o nome \"{name}\".")


def category_not_found(category_id) -> EntityNotFoundError:
    return EntityNotFoundError("Category", category_id, f"Categoria com ID {category_id} não encontrada.")


def category_has_dependencies(category_id) -> EntityHasDependenciesError:
    return EntityHasDependenciesError(
        "Category",
        category_id,
        "Não é possível excluir a categoria pois existem dependências vinculadas a ela (transações).",
    )
