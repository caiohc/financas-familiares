import uuid
from typing import Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.financial.entities import Category
from domain.financial.exceptions import category_already_exists
from domain.financial.repositories import CategoryRepository

from infrastructure.database.models import CategoryModel
from infrastructure.repositories.sqlalchemy.dependencies import has_dependent_rows

class SQLAlchemyCategoryRepository(CategoryRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: CategoryModel) -> Category:
        return Category(id=uuid.UUID(model.id), name=model.name, type=model.type)

    def _to_model(self, entity: Category) -> CategoryModel:
        return CategoryModel(id=str(entity.id), name=entity.name, type=entity.type)

    def save(self, category: Category) -> None:
        model = self._to_model(category)
        try:
            self.session.merge(model)
            self.session.flush()
        except IntegrityError:
            # Rede de segurança contra corrida entre a checagem em CategoryService e este flush.
            self.session.rollback()
            raise category_already_exists(category.name)

    def get_by_id(self, category_id: uuid.UUID) -> Optional[Category]:
        model = self.session.get(CategoryModel, str(category_id))
        return self._to_domain(model) if model else None

    def get_by_name(self, name: str) -> Optional[Category]:
        model = (
            self.session.query(CategoryModel)
            .filter(func.lower(CategoryModel.name) == name.lower())
            .first()
        )
        return self._to_domain(model) if model else None

    def list_all(self) -> list[Category]:
        return [self._to_domain(m) for m in self.session.query(CategoryModel).all()]

    def delete(self, category_id: uuid.UUID) -> None:
        model = self.session.get(CategoryModel, str(category_id))
        if model:
            self.session.delete(model)
            self.session.flush()

    def has_dependencies(self, category_id: uuid.UUID) -> bool:
        return has_dependent_rows(self.session, CategoryModel.__tablename__, str(category_id))
