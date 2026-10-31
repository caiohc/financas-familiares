import uuid
from typing import List, Optional

from application.dtos.financial_dtos import (
    CategoryResponseDTO,
    CreateCategoryDTO,
    SeedResultDTO,
    UpdateCategoryDTO,
)
from application.dtos.shared_dtos import DEFAULT_PAGE_SIZE, DeletionPreviewDTO, PageDTO
from application.services.pagination import build_page
from application.interfaces.unit_of_work import AbstractUnitOfWork
from domain.financial.entities import Category
from domain.financial.exceptions import category_already_exists, category_has_dependencies, category_not_found

class CategoryService:
    """
    Orquestra as operações de negócio de categoria.
    Sem nenhum acoplamento com Web, HTTP ou SQL.
    """
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    def _to_dto(self, category: Category) -> CategoryResponseDTO:
        return CategoryResponseDTO(id=category.id, name=category.name, type=category.type)

    def create_category(self, dto: CreateCategoryDTO) -> CategoryResponseDTO:
        with self.uow:
            category = Category(name=dto.name, type=dto.type)

            if self.uow.categories.get_by_name(category.name):
                raise category_already_exists(category.name)

            self.uow.categories.save(category)
            self.uow.commit()
            return self._to_dto(category)

    def get_category(self, category_id: uuid.UUID) -> CategoryResponseDTO:
        with self.uow:
            category = self.uow.categories.get_by_id(category_id)
            if not category:
                raise category_not_found(category_id)
            return self._to_dto(category)

    def list_categories(self) -> List[CategoryResponseDTO]:
        with self.uow:
            categories = sorted(self.uow.categories.list_all(), key=lambda c: (c.type.value, c.name.lower()))
            return [self._to_dto(c) for c in categories]

    def list_categories_page(
        self, page: Optional[int] = 1, page_size: Optional[int] = DEFAULT_PAGE_SIZE,
        sort_by: Optional[str] = None, sort_dir: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PageDTO[CategoryResponseDTO]:
        with self.uow:
            return build_page(
                self.uow.categories.list_page, self._to_dto, page, page_size, sort_by, sort_dir, ("name", "type"), search,
            )

    def update_category(self, category_id: uuid.UUID, dto: UpdateCategoryDTO) -> CategoryResponseDTO:
        with self.uow:
            category = self.uow.categories.get_by_id(category_id)
            if not category:
                raise category_not_found(category_id)

            # Valida tudo antes de alterar a entidade, para não deixá-la pela metade.
            new_name = Category.normalize_name(dto.name)
            new_type = Category.validate_type(dto.type)

            existing = self.uow.categories.get_by_name(new_name)
            if existing and existing.id != category_id:
                raise category_already_exists(new_name)

            category.rename(new_name)
            category.change_type(new_type)
            self.uow.categories.save(category)
            self.uow.commit()
            return self._to_dto(category)

    def preview_category_deletion(self, category_id: uuid.UUID) -> DeletionPreviewDTO:
        """Antecipa, para a tela de confirmação, se a exclusão será bloqueada e por quê."""
        with self.uow:
            category = self.uow.categories.get_by_id(category_id)
            if not category:
                raise category_not_found(category_id)

            blocked = self.uow.categories.has_dependencies(category_id)
            reason = str(category_has_dependencies(category_id)) if blocked else None
            return DeletionPreviewDTO(name=category.name, blocked_reason=reason)

    def delete_category(self, category_id: uuid.UUID) -> None:
        with self.uow:
            category = self.uow.categories.get_by_id(category_id)
            if not category:
                raise category_not_found(category_id)

            if self.uow.categories.has_dependencies(category_id):
                raise category_has_dependencies(category_id)

            self.uow.categories.delete(category_id)
            self.uow.commit()

    def seed_default_categories(self, defaults: List[CreateCategoryDTO]) -> SeedResultDTO:
        """
        Carga idempotente das categorias padrão: as que já existem (pelo nome,
        sem diferenciar caixa) são ignoradas. Todas são validadas antes de
        gravar qualquer uma, então um item inválido não deixa carga parcial.
        """
        with self.uow:
            candidates = [Category(name=d.name, type=d.type) for d in defaults]
            missing = [c for c in candidates if not self.uow.categories.get_by_name(c.name)]

            for category in missing:
                self.uow.categories.save(category)
            if missing:
                self.uow.commit()

            return SeedResultDTO(created=len(missing), skipped=len(candidates) - len(missing))
