import uuid
from typing import Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.family.entities import FamilyCostCenter
from domain.family.exceptions import FamilyCostCenterAlreadyExistsError
from domain.family.repositories import FamilyCostCenterRepository

from infrastructure.database.models import FamilyCostCenterModel

class SQLAlchemyFamilyCostCenterRepository(FamilyCostCenterRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: FamilyCostCenterModel) -> FamilyCostCenter:
        return FamilyCostCenter(
            id=uuid.UUID(model.id),
            family_id=uuid.UUID(model.family_id),
            name=model.name,
            description=model.description,
        )

    def _to_model(self, entity: FamilyCostCenter) -> FamilyCostCenterModel:
        return FamilyCostCenterModel(
            id=str(entity.id),
            family_id=str(entity.family_id),
            name=entity.name,
            description=entity.description,
        )

    def save(self, cost_center: FamilyCostCenter) -> None:
        model = self._to_model(cost_center)
        try:
            self.session.merge(model)
            self.session.flush()
        except IntegrityError:
            # Rede de segurança contra corrida entre a checagem em
            # FamilyCostCenterService e este flush.
            self.session.rollback()
            raise FamilyCostCenterAlreadyExistsError(cost_center.family_id, cost_center.name)

    def get_by_id(self, cost_center_id: uuid.UUID) -> Optional[FamilyCostCenter]:
        model = self.session.get(FamilyCostCenterModel, str(cost_center_id))
        return self._to_domain(model) if model else None

    def get_by_name(self, family_id: uuid.UUID, name: str) -> Optional[FamilyCostCenter]:
        model = (
            self.session.query(FamilyCostCenterModel)
            .filter(
                FamilyCostCenterModel.family_id == str(family_id),
                func.lower(FamilyCostCenterModel.name) == name.lower(),
            )
            .first()
        )
        return self._to_domain(model) if model else None

    def list_by_family(self, family_id: uuid.UUID) -> list[FamilyCostCenter]:
        models = (
            self.session.query(FamilyCostCenterModel)
            .filter(FamilyCostCenterModel.family_id == str(family_id))
            .all()
        )
        return [self._to_domain(m) for m in models]

    def delete(self, cost_center_id: uuid.UUID) -> None:
        model = self.session.get(FamilyCostCenterModel, str(cost_center_id))
        if model:
            self.session.delete(model)
            self.session.flush()
