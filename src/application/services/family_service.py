import uuid
from typing import List

from application.dtos.family_dtos import CreateFamilyDTO, UpdateFamilyDTO, FamilyResponseDTO
from application.interfaces.unit_of_work import AbstractUnitOfWork
from domain.family.entities import Family

class FamilyService:
    """
    Orquestra as operações de negócio da família.
    Sem nenhum acoplamento com Web, HTTP ou SQL.
    """
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    def _to_dto(self, family: Family) -> FamilyResponseDTO:
        return FamilyResponseDTO(
            id=family.id,
            name=family.name,
            current_balance=family.current_balance
        )

    def create_family(self, dto: CreateFamilyDTO) -> FamilyResponseDTO:
        with self.uow:
            family = Family(name=dto.name)
            self.uow.families.save(family)
            self.uow.commit()
            return self._to_dto(family)

    def get_family(self, family_id: uuid.UUID) -> FamilyResponseDTO:
        with self.uow:
            family = self.uow.families.get_by_id(family_id)
            if not family:
                raise ValueError(f"Família com ID {family_id} não encontrada.")
            return self._to_dto(family)

    def list_families(self) -> List[FamilyResponseDTO]:
        with self.uow:
            families = self.uow.families.list_all()
            return [self._to_dto(f) for f in families]

    def update_family(self, family_id: uuid.UUID, dto: UpdateFamilyDTO) -> FamilyResponseDTO:
        with self.uow:
            family = self.uow.families.get_by_id(family_id)
            if not family:
                raise ValueError(f"Família com ID {family_id} não encontrada.")
            
            family.name = dto.name
            self.uow.families.save(family)
            self.uow.commit()
            return self._to_dto(family)

    def delete_family(self, family_id: uuid.UUID) -> None:
        with self.uow:
            family = self.uow.families.get_by_id(family_id)
            if not family:
                raise ValueError(f"Família com ID {family_id} não encontrada.")
                
            if self.uow.families.has_dependencies(family_id):
                raise ValueError("Não é possível excluir a família pois existem dependências (membros, contas) vinculadas a ela.")
            
            self.uow.families.delete(family_id)
            self.uow.commit()
