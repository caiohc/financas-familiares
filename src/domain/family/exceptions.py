"""
Mensagens das exceções do domínio de Família.

Não são classes novas: cada função devolve uma das exceções compartilhadas de
domain/shared/exceptions.py com a mensagem do caso. Assim o texto fica num
lugar só, mesmo quando serviço e repositório levantam a mesma exceção.
"""
from domain.shared.exceptions import (
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)


def family_not_found(family_id) -> EntityNotFoundError:
    return EntityNotFoundError("Family", family_id, f"Família com ID {family_id} não encontrada.")


def family_has_dependencies(family_id) -> EntityHasDependenciesError:
    return EntityHasDependenciesError(
        "Family",
        family_id,
        "Não é possível excluir a família pois existem dependências vinculadas a ela "
        "(membros, centros de custo, contas ou transações).",
    )


def member_already_exists(name: str) -> EntityAlreadyExistsError:
    return EntityAlreadyExistsError(
        "Member", "name", name, f"Já existe um membro com o nome \"{name}\" nesta família."
    )


def member_not_found(member_id) -> EntityNotFoundError:
    return EntityNotFoundError("Member", member_id, f"Membro com ID {member_id} não encontrado.")


def member_has_dependencies(member_id) -> EntityHasDependenciesError:
    return EntityHasDependenciesError(
        "Member",
        member_id,
        "Não é possível excluir o membro pois existem dependências vinculadas a ele (contas ou cartões).",
    )


def cost_center_already_exists(name: str) -> EntityAlreadyExistsError:
    return EntityAlreadyExistsError(
        "FamilyCostCenter", "name", name,
        f"Já existe um centro de custo com o nome \"{name}\" nesta família.",
    )


def cost_center_not_found(cost_center_id) -> EntityNotFoundError:
    return EntityNotFoundError(
        "FamilyCostCenter", cost_center_id, f"Centro de custo com ID {cost_center_id} não encontrado."
    )


def cost_center_has_dependencies(cost_center_id) -> EntityHasDependenciesError:
    return EntityHasDependenciesError(
        "FamilyCostCenter",
        cost_center_id,
        "Não é possível excluir o centro de custo pois existem dependências vinculadas a ele (transações).",
    )
