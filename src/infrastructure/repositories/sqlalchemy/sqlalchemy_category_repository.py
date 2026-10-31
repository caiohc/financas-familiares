import uuid
from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.financial.entities import Category
from domain.financial.exceptions import category_already_exists
from domain.financial.repositories import CategoryRepository
from domain.shared.pagination import Page
from domain.shared.text import fold_text

from infrastructure.database.models import CategoryModel
from infrastructure.repositories.sqlalchemy.dependencies import has_dependent_rows

def _contains(column, term: str):
    """Condição "contém o trecho", sem caixa e sem acentos; %, _ e \\ do termo valem como texto."""
    escaped = fold_text(term).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return func.fold(column).like(f"%{escaped}%", escape="\\")

SORTABLE_FIELDS = ("name", "type")

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

    def list_page(
        self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
        search: Optional[str] = None,
    ) -> Page[Category]:
        if sort_by not in SORTABLE_FIELDS:
            raise ValueError(f"Campo de ordenação inválido: {sort_by!r}.")
        name = func.lower(CategoryModel.name)
        query = self.session.query(CategoryModel)
        if search:
            # O tipo é guardado como enum; a pesquisa vale sobre o rótulo que a pessoa vê.
            query = query.filter(or_(
                _contains(CategoryModel.name, search),
                CategoryModel.type.in_(Category.types_matching(search)),
            ))
        if sort_by == "type":
            # Os rótulos seguem a mesma ordem alfabética dos valores do enum; empates por nome e id.
            order = [func.lower(CategoryModel.type).desc() if descending else func.lower(CategoryModel.type).asc(), name.asc(), CategoryModel.id]
        else:
            order = [name.desc() if descending else name.asc(), CategoryModel.id]
        total = query.with_entities(func.count(CategoryModel.id)).scalar()
        models = query.order_by(*order).offset((page - 1) * page_size).limit(page_size).all()
        return Page(items=[self._to_domain(m) for m in models], total=total)

    def delete(self, category_id: uuid.UUID) -> None:
        model = self.session.get(CategoryModel, str(category_id))
        if model:
            self.session.delete(model)
            self.session.flush()

    def has_dependencies(self, category_id: uuid.UUID) -> bool:
        return has_dependent_rows(self.session, CategoryModel.__tablename__, str(category_id))
