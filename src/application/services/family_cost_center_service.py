import uuid
from typing import List

from application.dtos.family_dtos import (
    CreateFamilyCostCenterDTO,
    UpdateFamilyCostCenterDTO,
    FamilyCostCenterResponseDTO,
)
from application.interfaces.unit_of_work import AbstractUnitOfWork
from domain.family.entities import FamilyCostCenter
from domain.family.exceptions import (
    FamilyCostCenterAlreadyExistsError,
    FamilyCostCenterNotFoundError,
)

class FamilyCostCenterService:
    """
    Orquestra as operações de negócio de centro de custo.
    Sem nenhum acoplamento com Web, HTTP ou SQL.
    """
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    def _to_dto(self, cost_center: FamilyCostCenter) -> FamilyCostCenterResponseDTO:
        return FamilyCostCenterResponseDTO(
            id=cost_center.id,
            family_id=cost_center.family_id,
            name=cost_center.name,
            description=cost_center.description,
        )

    def create_family_cost_center(self, dto: CreateFamilyCostCenterDTO) -> FamilyCostCenterResponseDTO:
        with self.uow:
            if self.uow.family_cost_centers.get_by_name(dto.family_id, dto.name):
                raise FamilyCostCenterAlreadyExistsError(dto.family_id, dto.name)

            cost_center = FamilyCostCenter(
                family_id=dto.family_id, name=dto.name, description=dto.description
            )
            self.uow.family_cost_centers.save(cost_center)
            self.uow.commit()
            return self._to_dto(cost_center)

    def get_family_cost_center(self, cost_center_id: uuid.UUID) -> FamilyCostCenterResponseDTO:
        with self.uow:
            cost_center = self.uow.family_cost_centers.get_by_id(cost_center_id)
            if not cost_center:
                raise FamilyCostCenterNotFoundError(cost_center_id)
            return self._to_dto(cost_center)

    def list_family_cost_centers(self, family_id: uuid.UUID) -> List[FamilyCostCenterResponseDTO]:
        with self.uow:
            cost_centers = self.uow.family_cost_centers.list_by_family(family_id)
            return [self._to_dto(cc) for cc in cost_centers]

    def update_family_cost_center(
        self, cost_center_id: uuid.UUID, dto: UpdateFamilyCostCenterDTO
    ) -> FamilyCostCenterResponseDTO:
        with self.uow:
            cost_center = self.uow.family_cost_centers.get_by_id(cost_center_id)
            if not cost_center:
                raise FamilyCostCenterNotFoundError(cost_center_id)

            existing = self.uow.family_cost_centers.get_by_name(cost_center.family_id, dto.name)
            if existing and existing.id != cost_center_id:
                raise FamilyCostCenterAlreadyExistsError(cost_center.family_id, dto.name)

            cost_center.name = dto.name
            cost_center.description = dto.description
            self.uow.family_cost_centers.save(cost_center)
            self.uow.commit()
            return self._to_dto(cost_center)

    def delete_family_cost_center(self, cost_center_id: uuid.UUID) -> None:
        with self.uow:
            cost_center = self.uow.family_cost_centers.get_by_id(cost_center_id)
            if not cost_center:
                raise FamilyCostCenterNotFoundError(cost_center_id)

            self.uow.family_cost_centers.delete(cost_center_id)
            self.uow.commit()
