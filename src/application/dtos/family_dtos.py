import uuid
from dataclasses import dataclass

@dataclass(kw_only=True)
class CreateFamilyDTO:
    """Dados de entrada brutos oriundos da futura API/CLI para criação da família."""
    name: str

@dataclass(kw_only=True)
class CreateMemberDTO:
    """Entrada bruta para criar um Membro e validá-lo contra injeções nulas antes de virar Entidade."""
    family_id: uuid.UUID
    name: str
