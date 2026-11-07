import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from domain.identity.invitations import Invitation
from domain.identity.repositories import InvitationRepository

from infrastructure.database.models import UserInvitationModel

M = UserInvitationModel


class SQLAlchemyInvitationRepository(InvitationRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: UserInvitationModel) -> Invitation:
        return Invitation(
            id=uuid.UUID(model.id),
            user_id=uuid.UUID(model.user_id),
            purpose=model.purpose,
            token_hash=model.token_hash,
            code_hash=model.code_hash,
            created_by_user_id=uuid.UUID(model.created_by_user_id) if model.created_by_user_id else None,
            created_at=model.created_at,
            expires_at=model.expires_at,
            attempts=model.attempts,
            consumed_at=model.consumed_at,
            revoked_at=model.revoked_at,
        )

    def _to_model(self, entity: Invitation) -> UserInvitationModel:
        return UserInvitationModel(
            id=str(entity.id),
            user_id=str(entity.user_id),
            purpose=entity.purpose,
            token_hash=entity.token_hash,
            code_hash=entity.code_hash,
            created_by_user_id=str(entity.created_by_user_id) if entity.created_by_user_id else None,
            created_at=entity.created_at,
            expires_at=entity.expires_at,
            attempts=entity.attempts,
            consumed_at=entity.consumed_at,
            revoked_at=entity.revoked_at,
        )

    def save(self, invitation: Invitation) -> None:
        self.session.merge(self._to_model(invitation))
        self.session.flush()

    def get_by_token_hash(self, token_hash: str) -> Optional[Invitation]:
        model = self.session.query(M).filter(M.token_hash == token_hash).first()
        return self._to_domain(model) if model else None

    def get_active_for_user(self, user_id: uuid.UUID) -> Optional[Invitation]:
        model = (
            self.session.query(M)
            .filter(M.user_id == str(user_id), M.consumed_at.is_(None), M.revoked_at.is_(None))
            .first()
        )
        return self._to_domain(model) if model else None

    def revoke_active_for_user(self, user_id: uuid.UUID, now: datetime) -> None:
        self.session.execute(
            update(M)
            .where(M.user_id == str(user_id), M.consumed_at.is_(None), M.revoked_at.is_(None))
            .values(revoked_at=now)
            .execution_options(synchronize_session=False)
        )
        self.session.flush()

    def register_failed_attempt(self, invitation_id: uuid.UUID) -> None:
        # Incremento feito pelo banco (attempts = attempts + 1): duas tentativas simultâneas somam as duas.
        self.session.execute(
            update(M)
            .where(M.id == str(invitation_id))
            .values(attempts=M.attempts + 1)
            .execution_options(synchronize_session=False)
        )
        self.session.flush()

    def consume(self, invitation_id: uuid.UUID, now: datetime, max_attempts: int) -> bool:
        result = self.session.execute(
            update(M)
            .where(
                M.id == str(invitation_id),
                M.consumed_at.is_(None),
                M.revoked_at.is_(None),
                M.expires_at > now,
                M.attempts < max_attempts,
            )
            .values(consumed_at=now)
            .execution_options(synchronize_session=False)
        )
        self.session.flush()
        return result.rowcount == 1

    def delete_for_user(self, user_id: uuid.UUID) -> None:
        self.session.execute(
            delete(M).where(M.user_id == str(user_id)).execution_options(synchronize_session=False)
        )
        self.session.flush()
