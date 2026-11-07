"""
Exceções compartilhadas por todos os domínios.

Uma classe por *tipo* de falha, não por entidade nem por atributo: quem levanta
informa a entidade/campo envolvido e a mensagem já pronta para o usuário (em
pt-BR, com a concordância de gênero que só quem conhece a entidade sabe fazer).
Cada domínio centraliza suas mensagens em funções (ex.: domain/family/exceptions.py).
"""


class DomainValidationError(ValueError):
    """Atributo inválido em uma entidade. `field` diz qual campo falhou."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


class EntityNotFoundError(ValueError):
    """A entidade referenciada não existe."""

    def __init__(self, entity: str, entity_id, message: str):
        super().__init__(message)
        self.entity = entity
        self.entity_id = entity_id


class EntityAlreadyExistsError(ValueError):
    """Violação de unicidade: já existe uma entidade com este valor em `field`."""

    def __init__(self, entity: str, field: str, value, message: str):
        super().__init__(message)
        self.entity = entity
        self.field = field
        self.value = value


class EntityHasDependenciesError(ValueError):
    """A entidade não pode ser excluída pois há outras entidades vinculadas a ela."""

    def __init__(self, entity: str, entity_id, message: str):
        super().__init__(message)
        self.entity = entity
        self.entity_id = entity_id


class AccessDeniedError(ValueError):
    """O ator autenticado não tem permissão para a operação (HTTP 403)."""

    def __init__(self, action: str, message: str):
        super().__init__(message)
        self.action = action


class AuthenticationFailedError(ValueError):
    """Credencial, convite ou link inválido. A mensagem é propositalmente genérica."""

    def __init__(self, message: str):
        super().__init__(message)
