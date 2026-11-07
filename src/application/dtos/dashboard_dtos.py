from dataclasses import dataclass

@dataclass(kw_only=True)
class EntityCountsDTO:
    families: int
    members: int
    users: int
    cost_centers: int
    categories: int
