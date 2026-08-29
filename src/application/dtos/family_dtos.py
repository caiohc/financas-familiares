from uuid import UUID
from dataclasses import dataclass
from decimal import Decimal

@dataclass(kw_only=True)
class CreateFamilyDTO:
    name: str

@dataclass(kw_only=True)
class UpdateFamilyDTO:
    name: str

@dataclass(kw_only=True)
class FamilyResponseDTO:
    id: UUID
    name: str
    current_balance: Decimal

@dataclass(kw_only=True)
class CreateMemberDTO:
    family_id: UUID
    name: str

