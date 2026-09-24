class FamilyAlreadyExistsError(ValueError):
    """Violação da regra de unicidade: já existe uma família com este nome."""

    def __init__(self, name: str):
        super().__init__(f"Já existe uma família com o nome \"{name}\".")
        self.name = name
