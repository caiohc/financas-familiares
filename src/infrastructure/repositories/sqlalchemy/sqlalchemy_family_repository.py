import uuid
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from domain.family.entities import Family
from domain.shared.pagination import Page
from domain.shared.text import fold_text
from domain.family.repositories import FamilyRepository

from infrastructure.database.models import FamilyModel
from infrastructure.repositories.sqlalchemy.dependencies import has_dependent_rows

def _contains(column, term: str):
    """Condição "contém o trecho", sem caixa e sem acentos; %, _ e \\ do termo valem como texto."""
    escaped = fold_text(term).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return func.fold(column).like(f"%{escaped}%", escape="\\")


class SQLAlchemyFamilyRepository(FamilyRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: FamilyModel) -> Family:
        return Family(
            id=uuid.UUID(model.id),
            name=model.name,
            current_balance=model.current_balance
        )

    def _to_model(self, entity: Family) -> FamilyModel:
        return FamilyModel(
            id=str(entity.id),
            name=entity.name,
            current_balance=entity.current_balance
        )

    def save(self, family: Family) -> None:
        self.session.merge(self._to_model(family))
        self.session.flush()

    def get_by_id(self, family_id: uuid.UUID) -> Optional[Family]:
        model = self.session.get(FamilyModel, str(family_id))
        return self._to_domain(model) if model else None

    def list_all(self) -> list[Family]:
        models = self.session.query(FamilyModel).all()
        return [self._to_domain(m) for m in models]

    def list_page(
        self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
        search: Optional[str] = None,
    ) -> Page[Family]:
        if sort_by != "name":
            raise ValueError(f"Campo de ordenação inválido: {sort_by!r}.")
        name = func.lower(FamilyModel.name)
        query = self.session.query(FamilyModel)
        if search:
            query = query.filter(_contains(FamilyModel.name, search))
        total = query.with_entities(func.count(FamilyModel.id)).scalar()
        models = (
            query.order_by(name.desc() if descending else name.asc(), FamilyModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return Page(items=[self._to_domain(m) for m in models], total=total)

    def delete(self, family_id: uuid.UUID) -> None:
        model = self.session.get(FamilyModel, str(family_id))
        if model:
            self.session.delete(model)
            self.session.flush()

    def has_dependencies(self, family_id: uuid.UUID) -> bool:
        return has_dependent_rows(self.session, FamilyModel.__tablename__, str(family_id))

