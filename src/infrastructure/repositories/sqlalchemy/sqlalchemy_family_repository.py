import uuid
from typing import Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.family.entities import Family
from domain.family.exceptions import FamilyAlreadyExistsError

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
        try:
            self.session.merge(model)
            self.session.flush()
        except IntegrityError:
            # Rede de segurança contra corrida entre a checagem em FamilyService
            # e este flush: outra transação pode ter inserido o mesmo nome nesse meio-tempo.
            self.session.rollback()
            raise FamilyAlreadyExistsError(family.name)

    def get_by_id(self, family_id: uuid.UUID) -> Optional[Family]:
        model = self.session.get(FamilyModel, str(family_id))
        return self._to_domain(model) if model else None

    def get_by_name(self, name: str) -> Optional[Family]:
        model = (
            self.session.query(FamilyModel)
            .filter(func.lower(FamilyModel.name) == name.lower())
            .first()
        )
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

