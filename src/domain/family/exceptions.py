class FamilyAlreadyExistsError(ValueError):
    """Violação da regra de unicidade: já existe uma família com este nome."""

    def __init__(self, name: str):
        super().__init__(f"Já existe uma família com o nome \"{name}\".")
        self.name = name


class FamilyNotFoundError(ValueError):
    """A família referenciada não existe."""

    def __init__(self, family_id):
        super().__init__(f"Família com ID {family_id} não encontrada.")
        self.family_id = family_id


class FamilyHasDependenciesError(ValueError):
    """A família não pode ser excluída pois há entidades vinculadas a ela."""

    def __init__(self, family_id):
        super().__init__(
            "Não é possível excluir a família pois existem dependências "
            "(membros, contas) vinculadas a ela."
        )
        self.family_id = family_id


class FamilyCostCenterAlreadyExistsError(ValueError):
    """Violação da unicidade por família: já existe um centro de custo com este nome nesta família."""

    def __init__(self, family_id, name: str):
        super().__init__(
            f"Já existe um centro de custo com o nome \"{name}\" nesta família."
        )
        self.family_id = family_id
        self.name = name


class FamilyCostCenterNotFoundError(ValueError):
    """O centro de custo referenciado não existe."""

    def __init__(self, cost_center_id):
        super().__init__(f"Centro de custo com ID {cost_center_id} não encontrado.")
        self.cost_center_id = cost_center_id
