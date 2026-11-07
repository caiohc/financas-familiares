"""
Mensagens das exceções do domínio de Identidade.

Não são classes novas: cada função devolve uma das exceções compartilhadas de
domain/shared/exceptions.py com a mensagem do caso (ver domain/family/exceptions.py).

As mensagens de autenticação (credencial, convite, link) são propositalmente genéricas:
nunca revelam se o usuário existe, se a conta está pendente ou desativada, nem qual
parte da credencial falhou.
"""
from domain.shared.exceptions import (
    AccessDeniedError,
    AuthenticationFailedError,
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)


def family_required_for_role() -> DomainValidationError:
    return DomainValidationError("family_id", "Usuário administrador da família ou comum deve pertencer a uma família.")


def family_not_allowed_for_system_roles() -> DomainValidationError:
    return DomainValidationError("family_id", "Usuário root ou administrador do sistema não pode pertencer a uma família.")


def root_requires_password() -> DomainValidationError:
    return DomainValidationError("password", "O usuário root precisa ter senha.")


def email_invalid() -> DomainValidationError:
    return DomainValidationError("email", "Informe um e-mail válido.")


def email_confirmation_mismatch() -> DomainValidationError:
    return DomainValidationError("email_confirmation", "Os e-mails informados não conferem.")


def email_locked_after_activation() -> DomainValidationError:
    return DomainValidationError(
        "email",
        "O e-mail não pode ser alterado depois que a conta foi ativada: só o próprio usuário pode alterá-lo.",
    )


def username_already_exists(username: str) -> EntityAlreadyExistsError:
    return EntityAlreadyExistsError(
        "User", "username", username, f"Já existe um usuário com o nome de usuário \"{username}\"."
    )


def email_already_exists(email: str) -> EntityAlreadyExistsError:
    return EntityAlreadyExistsError("User", "email", email, f"Já existe um usuário com o e-mail \"{email}\".")


def root_already_exists() -> EntityAlreadyExistsError:
    return EntityAlreadyExistsError(
        "User", "role", "ROOT",
        "Já existe um usuário root. O sistema permite um único root, então um segundo não pode ser criado.",
    )


def username_in_use(username: str) -> EntityAlreadyExistsError:
    return EntityAlreadyExistsError(
        "User", "username", username, f'O nome de usuário "{username}" já está cadastrado no sistema.'
    )


def email_in_use(email: str) -> EntityAlreadyExistsError:
    return EntityAlreadyExistsError("User", "email", email, f'O e-mail "{email}" já está cadastrado no sistema.')


def email_unchanged() -> DomainValidationError:
    return DomainValidationError("email", "O novo e-mail é igual ao atual.")


def root_not_found() -> EntityNotFoundError:
    return EntityNotFoundError("User", "ROOT", "Ainda não existe usuário root: crie-o com o comando create-root.")


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


def cannot_deactivate_root() -> DomainValidationError:
    return DomainValidationError("is_active", "O usuário root não pode ser desativado.")


def cannot_act_on_self(action: str) -> DomainValidationError:
    return DomainValidationError("user", f"Você não pode {action} a sua própria conta.")


# --- Autorização das operações sobre contas ---

def access_denied(action: str) -> AccessDeniedError:
    return AccessDeniedError(action, "Você não tem permissão para realizar esta operação.")


# --- Autenticação (mensagens genéricas) ---

def invalid_credentials() -> AuthenticationFailedError:
    return AuthenticationFailedError("Usuário ou senha inválidos.")


def invalid_invitation() -> AuthenticationFailedError:
    return AuthenticationFailedError("Convite ou código inválido, expirado ou já utilizado.")


def invalid_recovery_link() -> AuthenticationFailedError:
    return AuthenticationFailedError("Link inválido, expirado ou já utilizado.")


def invalid_current_password() -> DomainValidationError:
    return DomainValidationError("current_password", "A senha atual não confere.")


def new_password_same_as_current() -> DomainValidationError:
    return DomainValidationError("password", "A nova senha deve ser diferente da atual.")


# --- Convites ---

def access_already_defined() -> DomainValidationError:
    return DomainValidationError(
        "user",
        "Esta pessoa já definiu a própria senha. Usuários de família redefinem a senha por conta própria, "
        "em \"Esqueci minha senha\".",
    )


def account_deactivated() -> DomainValidationError:
    return DomainValidationError("user", "A conta está desativada. Reative-a antes de emitir um convite.")
