from uuid import UUID
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

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

@dataclass(kw_only=True)
class CreateFamilyCostCenterDTO:
    family_id: UUID
    name: str
    description: Optional[str] = None

@dataclass(kw_only=True)
class UpdateFamilyCostCenterDTO:
    name: str
    description: Optional[str] = None

@dataclass(kw_only=True)
class FamilyCostCenterResponseDTO:
    id: UUID
    family_id: UUID
    name: str
    description: Optional[str]

