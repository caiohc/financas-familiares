from dataclasses import dataclass

@dataclass(kw_only=True)
class EntityCountsDTO:
    families: int
    members: int
    cost_centers: int
    categories: int
