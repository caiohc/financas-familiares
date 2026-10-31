"""
Mensagens das exceções do domínio de Identidade.

Não são classes novas: cada função devolve uma das exceções compartilhadas de
domain/shared/exceptions.py com a mensagem do caso (ver domain/family/exceptions.py).
"""
from domain.shared.exceptions import (
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)


def family_required_for_role() -> DomainValidationError:
    return DomainValidationError("family_id", "Usuário administrador da família ou comum deve pertencer a uma família.")


def family_not_allowed_for_system_roles() -> DomainValidationError:
    return DomainValidationError("family_id", "Usuário root ou administrador do sistema não pode pertencer a uma família.")


def username_already_exists(username: str) -> EntityAlreadyExistsError:
    return EntityAlreadyExistsError(
        "User", "username", username, f"Já existe um usuário com o nome de usuário \"{username}\"."
    )


def email_already_exists(email: str) -> EntityAlreadyExistsError:
    return EntityAlreadyExistsError("User", "email", email, f"Já existe um usuário com o e-mail \"{email}\".")


def root_already_exists() -> EntityAlreadyExistsError:
    return EntityAlreadyExistsError("User", "role", "ROOT", "Já existe um usuário root cadastrado.")


def user_not_found(user_id) -> EntityNotFoundError:
    return EntityNotFoundError("User", user_id, f"Usuário com ID {user_id} não encontrado.")


def user_has_dependencies(user_id) -> EntityHasDependenciesError:
    return EntityHasDependenciesError(
        "User", user_id, "Não é possível excluir o usuário pois existem dependências vinculadas a ele."
    )


def root_cannot_be_deleted(user_id) -> EntityHasDependenciesError:
    return EntityHasDependenciesError(
        "User", user_id, "Não é possível excluir o usuário root: ele é o acesso inicial da aplicação."
    )


def root_cannot_be_created() -> DomainValidationError:
    return DomainValidationError(
        "role", "O usuário root só pode ser criado pelo comando create-root."
    )
