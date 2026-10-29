import uuid
from typing import Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.family.entities import Member
from domain.family.exceptions import member_already_exists
from domain.family.repositories import MemberRepository

from infrastructure.database.models import MemberModel
from infrastructure.repositories.sqlalchemy.dependencies import has_dependent_rows

class SQLAlchemyMemberRepository(MemberRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: MemberModel) -> Member:
        return Member(
            id=uuid.UUID(model.id),
            family_id=uuid.UUID(model.family_id),
            name=model.name,
        )

    def _to_model(self, entity: Member) -> MemberModel:
        return MemberModel(
            id=str(entity.id),
            family_id=str(entity.family_id),
            name=entity.name,
        )

    def save(self, member: Member) -> None:
        model = self._to_model(member)
        try:
            self.session.merge(model)
            self.session.flush()
        except IntegrityError:
            # Rede de segurança contra corrida entre a checagem em MemberService e este flush.
            self.session.rollback()
            raise member_already_exists(member.name)

    def get_by_id(self, member_id: uuid.UUID) -> Optional[Member]:
        model = self.session.get(MemberModel, str(member_id))
        return self._to_domain(model) if model else None

    def get_by_name(self, family_id: uuid.UUID, name: str) -> Optional[Member]:
        model = (
            self.session.query(MemberModel)
            .filter(
                MemberModel.family_id == str(family_id),
                func.lower(MemberModel.name) == name.lower(),
            )
            .first()
        )
        return self._to_domain(model) if model else None

    def list_by_family(self, family_id: uuid.UUID) -> list[Member]:
        models = self.session.query(MemberModel).filter(MemberModel.family_id == str(family_id)).all()
        return [self._to_domain(m) for m in models]

    def list_all(self) -> list[Member]:
        models = self.session.query(MemberModel).all()
        return [self._to_domain(m) for m in models]

    def delete(self, member_id: uuid.UUID) -> None:
        model = self.session.get(MemberModel, str(member_id))
        if model:
            self.session.delete(model)
            self.session.flush()

    def has_dependencies(self, member_id: uuid.UUID) -> bool:
        return has_dependent_rows(self.session, MemberModel.__tablename__, str(member_id))
