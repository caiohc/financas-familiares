import uuid
from typing import List

from application.dtos.family_dtos import (
    CreateFamilyCostCenterDTO,
    UpdateFamilyCostCenterDTO,
    FamilyCostCenterResponseDTO,
)
from application.dtos.shared_dtos import DeletionPreviewDTO
from application.interfaces.unit_of_work import AbstractUnitOfWork
from domain.family.entities import FamilyCostCenter
from domain.family.exceptions import (
    cost_center_already_exists,
    cost_center_has_dependencies,
    cost_center_not_found,
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
            cost_center = FamilyCostCenter(
                family_id=dto.family_id, name=dto.name, description=dto.description
            )

            if self.uow.family_cost_centers.get_by_name(cost_center.family_id, cost_center.name):
                raise cost_center_already_exists(cost_center.name)

            self.uow.family_cost_centers.save(cost_center)
            self.uow.commit()
            return self._to_dto(cost_center)

    def get_family_cost_center(self, cost_center_id: uuid.UUID) -> FamilyCostCenterResponseDTO:
        with self.uow:
            cost_center = self.uow.family_cost_centers.get_by_id(cost_center_id)
            if not cost_center:
                raise cost_center_not_found(cost_center_id)
            return self._to_dto(cost_center)

    def list_family_cost_centers(self, family_id: uuid.UUID) -> List[FamilyCostCenterResponseDTO]:
        with self.uow:
            cost_centers = self._by_name(self.uow.family_cost_centers.list_by_family(family_id))
            return [self._to_dto(cc) for cc in cost_centers]

    def list_all_family_cost_centers(self) -> List[FamilyCostCenterResponseDTO]:
        """Provisório, sem escopo de família: ver AbstractRepository.list_all."""
        with self.uow:
            cost_centers = self._by_name(self.uow.family_cost_centers.list_all())
            return [self._to_dto(cc) for cc in cost_centers]

    @staticmethod
    def _by_name(cost_centers: List[FamilyCostCenter]) -> List[FamilyCostCenter]:
        return sorted(cost_centers, key=lambda cc: cc.name.lower())

    def preview_family_cost_center_deletion(self, cost_center_id: uuid.UUID) -> DeletionPreviewDTO:
        """Antecipa, para a tela de confirmação, se a exclusão será bloqueada e por quê."""
        with self.uow:
            cost_center = self.uow.family_cost_centers.get_by_id(cost_center_id)
            if not cost_center:
                raise cost_center_not_found(cost_center_id)

            blocked = self.uow.family_cost_centers.has_dependencies(cost_center_id)
            reason = str(cost_center_has_dependencies(cost_center_id)) if blocked else None
            return DeletionPreviewDTO(name=cost_center.name, blocked_reason=reason)

    def update_family_cost_center(
        self, cost_center_id: uuid.UUID, dto: UpdateFamilyCostCenterDTO
    ) -> FamilyCostCenterResponseDTO:
        with self.uow:
            cost_center = self.uow.family_cost_centers.get_by_id(cost_center_id)
            if not cost_center:
                raise cost_center_not_found(cost_center_id)

            new_name = FamilyCostCenter.normalize_name(dto.name)
            existing = self.uow.family_cost_centers.get_by_name(cost_center.family_id, new_name)
            if existing and existing.id != cost_center_id:
                raise cost_center_already_exists(new_name)

            cost_center.rename(new_name)
            cost_center.description = dto.description
            self.uow.family_cost_centers.save(cost_center)
            self.uow.commit()
            return self._to_dto(cost_center)

    def delete_family_cost_center(self, cost_center_id: uuid.UUID) -> None:
        with self.uow:
            cost_center = self.uow.family_cost_centers.get_by_id(cost_center_id)
            if not cost_center:
                raise cost_center_not_found(cost_center_id)

            if self.uow.family_cost_centers.has_dependencies(cost_center_id):
                raise cost_center_has_dependencies(cost_center_id)

            self.uow.family_cost_centers.delete(cost_center_id)
            self.uow.commit()
