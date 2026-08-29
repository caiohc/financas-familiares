import uuid
from typing import Optional
from sqlalchemy.orm import Session

from domain.family.entities import Family

from domain.family.repositories import FamilyRepository

from infrastructure.database.models import FamilyModel, MemberModel

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
        model = self._to_model(family)
        self.session.merge(model)
        self.session.flush()

    def get_by_id(self, family_id: uuid.UUID) -> Optional[Family]:
        model = self.session.get(FamilyModel, str(family_id))
        return self._to_domain(model) if model else None

    def list_all(self) -> list[Family]:
        models = self.session.query(FamilyModel).all()
        return [self._to_domain(m) for m in models]

    def delete(self, family_id: uuid.UUID) -> None:
        model = self.session.get(FamilyModel, str(family_id))
        if model:
            self.session.delete(model)
            self.session.flush()

    def has_dependencies(self, family_id: uuid.UUID) -> bool:
        return self.session.query(MemberModel).filter_by(family_id=str(family_id)).first() is not None

