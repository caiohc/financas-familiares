import uuid
from typing import List, Optional

from application.dtos.family_dtos import CreateFamilyDTO, UpdateFamilyDTO, FamilyResponseDTO
from application.dtos.shared_dtos import DeletionPreviewDTO
from application.dtos.shared_dtos import DEFAULT_PAGE_SIZE, PageDTO
from application.services.pagination import build_page
from application.interfaces.unit_of_work import AbstractUnitOfWork
from domain.family.entities import Family
from domain.family.exceptions import family_has_dependencies, family_not_found

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
                raise family_not_found(family_id)
            return self._to_dto(family)

    def list_families(self) -> List[FamilyResponseDTO]:
        with self.uow:
            families = sorted(self.uow.families.list_all(), key=lambda f: f.name.lower())
            return [self._to_dto(f) for f in families]

    def list_families_page(
        self, page: Optional[int] = 1, page_size: Optional[int] = DEFAULT_PAGE_SIZE,
        sort_by: Optional[str] = None, sort_dir: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PageDTO[FamilyResponseDTO]:
        with self.uow:
            return build_page(
                self.uow.families.list_page, self._to_dto, page, page_size, sort_by, sort_dir, ("name",), search,
            )

    def update_family(self, family_id: uuid.UUID, dto: UpdateFamilyDTO) -> FamilyResponseDTO:
        with self.uow:
            family = self.uow.families.get_by_id(family_id)
            if not family:
                raise family_not_found(family_id)

            family.rename(dto.name)
            self.uow.families.save(family)
            self.uow.commit()
            return self._to_dto(family)

    def preview_family_deletion(self, family_id: uuid.UUID) -> DeletionPreviewDTO:
        """Antecipa, para a tela de confirmação, se a exclusão será bloqueada e por quê."""
        with self.uow:
            family = self.uow.families.get_by_id(family_id)
            if not family:
                raise family_not_found(family_id)

            blocked = self.uow.families.has_dependencies(family_id)
            reason = str(family_has_dependencies(family_id)) if blocked else None
            return DeletionPreviewDTO(name=family.name, blocked_reason=reason)

    def delete_family(self, family_id: uuid.UUID) -> None:
        with self.uow:
            family = self.uow.families.get_by_id(family_id)
            if not family:
                raise family_not_found(family_id)

            if self.uow.families.has_dependencies(family_id):
                raise family_has_dependencies(family_id)

            self.uow.families.delete(family_id)
            self.uow.commit()
