"""Repositório de convites, com SQLite real: consumo atômico, tentativas, revogação e a regra de um convite ativo."""
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from domain.identity.entities import Role, User
from domain.identity.invitations import Invitation, InvitationPurpose, hash_token
from infrastructure.database.models import Base, FamilyModel
from infrastructure.repositories.sqlalchemy.sqlalchemy_invitation_repository import SQLAlchemyInvitationRepository
from infrastructure.repositories.sqlalchemy.sqlalchemy_user_repository import SQLAlchemyUserRepository

NOW = datetime(2026, 11, 8, 12, 0, 0)
MAX = 5


@pytest.fixture
def repo(session: Session) -> SQLAlchemyInvitationRepository:
    return SQLAlchemyInvitationRepository(session)


@pytest.fixture
def user(session: Session) -> User:
    family = FamilyModel(id=str(uuid.uuid4()), name="Silva")
    session.add(family)
    session.flush()
    user = User(
        role=Role.FAMILY_USER, family_id=uuid.UUID(family.id), name="Maria", username=f"maria{uuid.uuid4().hex[:6]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
    )
    SQLAlchemyUserRepository(session).save(user)
    session.flush()
    return user


def _invitation(user, purpose=InvitationPurpose.ACTIVATION, token="token-1", **overrides) -> Invitation:
    data = dict(
        user_id=user.id, purpose=purpose, token_hash=hash_token(token),
        code_hash="code-hash" if purpose.requires_code else None,
        created_at=NOW, expires_at=NOW + timedelta(hours=24),
    )
    data.update(overrides)
    return Invitation(**data)


def test_save_and_get_by_token_hash_round_trips_every_attribute(repo, user):
    invitation = _invitation(user, created_by_user_id=uuid.uuid4(), attempts=2)
    repo.save(invitation)

    assert repo.get_by_token_hash(hash_token("token-1")) == invitation


def test_recovery_invitation_round_trips_without_a_code(repo, user):
    invitation = _invitation(user, InvitationPurpose.RECOVERY)
    repo.save(invitation)

    fetched = repo.get_by_token_hash(invitation.token_hash)
    assert fetched.code_hash is None and fetched.purpose is InvitationPurpose.RECOVERY


def test_unknown_token_hash_returns_none(repo):
    assert repo.get_by_token_hash(hash_token("inexistente")) is None


@pytest.mark.parametrize("probe", ["' OR '1'='1", "%", "_", ""])
def test_token_lookup_is_exact_and_treats_input_as_text(repo, user, probe):
    repo.save(_invitation(user))
    assert repo.get_by_token_hash(probe) is None


def test_get_active_for_user(repo, user):
    assert repo.get_active_for_user(user.id) is None
    invitation = _invitation(user)
    repo.save(invitation)

    assert repo.get_active_for_user(user.id).id == invitation.id


# --- Um convite ativo por usuário (índice único parcial) ---

def test_the_database_allows_only_one_active_invitation_per_user(repo, session, user):
    repo.save(_invitation(user, token="um"))

    with pytest.raises(IntegrityError):
        repo.save(_invitation(user, token="dois"))


def test_a_new_invitation_is_allowed_once_the_previous_one_is_revoked(repo, user):
    repo.save(_invitation(user, token="um"))
    repo.revoke_active_for_user(user.id, NOW)

    repo.save(_invitation(user, token="dois"))

    assert repo.get_active_for_user(user.id).token_hash == hash_token("dois")


def test_a_new_invitation_is_allowed_once_the_previous_one_is_consumed(repo, user):
    first = _invitation(user, token="um")
    repo.save(first)
    assert repo.consume(first.id, NOW, MAX) is True

    repo.save(_invitation(user, token="dois"))


def test_the_token_hash_is_unique(repo, session, user):
    repo.save(_invitation(user, token="mesmo"))
    repo.revoke_active_for_user(user.id, NOW)

    with pytest.raises(IntegrityError):
        repo.save(_invitation(user, token="mesmo"))


def test_the_database_rejects_a_code_invitation_without_a_code_hash(session, user):
    # contorna a entidade (que também impede) para provar a trava do próprio banco
    with pytest.raises(IntegrityError):
        session.execute(text(
            "INSERT INTO user_invitations (id, user_id, purpose, token_hash, code_hash, created_at, expires_at, attempts) "
            "VALUES (:id, :user_id, 'ACTIVATION', :token_hash, NULL, :now, :now, 0)"
        ), {"id": str(uuid.uuid4()), "user_id": str(user.id), "token_hash": "x" * 64, "now": str(NOW)})
        session.flush()


def test_the_database_rejects_a_recovery_invitation_with_a_code_hash(session, user):
    with pytest.raises(IntegrityError):
        session.execute(text(
            "INSERT INTO user_invitations (id, user_id, purpose, token_hash, code_hash, created_at, expires_at, attempts) "
            "VALUES (:id, :user_id, 'RECOVERY', :token_hash, 'codigo', :now, :now, 0)"
        ), {"id": str(uuid.uuid4()), "user_id": str(user.id), "token_hash": "y" * 64, "now": str(NOW)})
        session.flush()


# --- Revogar ---

def test_revoke_active_marks_the_invitation_and_leaves_none_active(repo, user):
    invitation = _invitation(user)
    repo.save(invitation)

    repo.revoke_active_for_user(user.id, NOW + timedelta(hours=1))

    assert repo.get_active_for_user(user.id) is None
    assert repo.get_by_token_hash(invitation.token_hash).revoked_at == NOW + timedelta(hours=1)


def test_revoke_active_does_not_touch_other_users_invitations(repo, session, user):
    other = User(
        role=Role.FAMILY_USER, family_id=user.family_id, name="Outra", username="outra", email="outra@example.com",
    )
    SQLAlchemyUserRepository(session).save(other)
    session.flush()
    repo.save(_invitation(user, token="a"))
    repo.save(_invitation(other, token="b"))

    repo.revoke_active_for_user(user.id, NOW)

    assert repo.get_active_for_user(other.id) is not None


def test_revoke_with_nothing_active_is_a_noop(repo, user):
    repo.revoke_active_for_user(user.id, NOW)


# --- Tentativas erradas: incremento feito pelo banco ---

def test_failed_attempts_accumulate(repo, user):
    invitation = _invitation(user)
    repo.save(invitation)

    for _ in range(3):
        repo.register_failed_attempt(invitation.id)

    assert repo.get_by_token_hash(invitation.token_hash).attempts == 3


def test_failed_attempt_on_an_unknown_invitation_is_harmless(repo):
    repo.register_failed_attempt(uuid.uuid4())


# --- Consumo atômico ---

def test_consume_succeeds_once(repo, user):
    invitation = _invitation(user)
    repo.save(invitation)

    assert repo.consume(invitation.id, NOW, MAX) is True
    assert repo.consume(invitation.id, NOW, MAX) is False                    # segunda vez: já usado
    assert repo.get_by_token_hash(invitation.token_hash).consumed_at == NOW


@pytest.mark.parametrize("scenario", ["expired", "revoked", "attempts", "unknown"])
def test_consume_refuses_what_is_not_usable(repo, user, scenario):
    invitation = _invitation(user)
    repo.save(invitation)
    invitation_id = invitation.id
    when = NOW
    if scenario == "expired":
        when = invitation.expires_at                    # exatamente no prazo: já venceu
    elif scenario == "revoked":
        repo.revoke_active_for_user(user.id, NOW)
    elif scenario == "attempts":
        for _ in range(MAX):
            repo.register_failed_attempt(invitation.id)
    else:
        invitation_id = uuid.uuid4()

    assert repo.consume(invitation_id, when, MAX) is False
    assert repo.get_by_token_hash(invitation.token_hash).consumed_at is None


def test_consume_respects_the_attempt_limit_boundary(repo, user):
    invitation = _invitation(user)
    repo.save(invitation)
    for _ in range(MAX - 1):
        repo.register_failed_attempt(invitation.id)

    assert repo.consume(invitation.id, NOW, MAX) is True          # 4 erros ainda deixam passar


def test_a_second_consumer_on_another_connection_cannot_win(tmp_path):
    """Duas conexões independentes tentam consumir o mesmo convite: como a condição vai dentro do UPDATE (e
    não numa leitura seguida de gravação), só a primeira vence. (Não é um teste de paralelismo real.)"""
    engine = create_engine(f"sqlite:///{tmp_path / 'race.db'}", connect_args={"timeout": 5})
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine)

    with maker() as setup:
        family = FamilyModel(id=str(uuid.uuid4()), name="Silva")
        setup.add(family)
        setup.flush()
        user = User(role=Role.FAMILY_USER, family_id=uuid.UUID(family.id), name="Maria", username="maria", email="m@example.com")
        SQLAlchemyUserRepository(setup).save(user)
        invitation = _invitation(user)
        SQLAlchemyInvitationRepository(setup).save(invitation)
        setup.commit()

    outcomes = []
    for _ in range(2):
        with maker() as competitor:
            outcomes.append(SQLAlchemyInvitationRepository(competitor).consume(invitation.id, NOW, MAX))
            competitor.commit()

    assert sorted(outcomes) == [False, True]
    engine.dispose()


# --- Excluir com o usuário ---

def test_delete_for_user_removes_all_its_invitations_only(repo, session, user):
    other = User(
        role=Role.FAMILY_USER, family_id=user.family_id, name="Outra", username="outra", email="outra@example.com",
    )
    SQLAlchemyUserRepository(session).save(other)
    session.flush()
    repo.save(_invitation(user, token="a"))
    repo.revoke_active_for_user(user.id, NOW)
    repo.save(_invitation(user, token="b"))
    repo.save(_invitation(other, token="c"))

    repo.delete_for_user(user.id)

    assert repo.get_by_token_hash(hash_token("a")) is None and repo.get_by_token_hash(hash_token("b")) is None
    assert repo.get_by_token_hash(hash_token("c")) is not None


def test_delete_for_user_with_nothing_to_delete_is_a_noop(repo):
    repo.delete_for_user(uuid.uuid4())
