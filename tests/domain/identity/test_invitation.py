import uuid
from datetime import datetime, timedelta

import pytest

from domain.identity.invitations import (
    CODE_ALPHABET,
    CODE_LENGTH,
    Invitation,
    InvitationPurpose,
    format_code,
    generate_code,
    generate_token,
    hash_token,
    normalize_code,
)
from domain.shared.exceptions import AuthenticationFailedError

NOW = datetime(2026, 11, 8, 12, 0, 0)


def _invitation(purpose=InvitationPurpose.ACTIVATION, **overrides) -> Invitation:
    data = dict(
        user_id=uuid.uuid4(), purpose=purpose, token_hash=hash_token("t"),
        code_hash="code-hash" if purpose.requires_code else None,
        created_at=NOW, expires_at=NOW + timedelta(hours=24),
    )
    data.update(overrides)
    return Invitation(**data)


# --- Token e código ---

def test_tokens_are_long_unique_and_url_safe():
    tokens = {generate_token() for _ in range(200)}
    assert len(tokens) == 200
    assert all(len(t) >= 43 and all(c.isalnum() or c in "-_" for c in t) for t in tokens)


def test_token_hash_is_deterministic_hex_and_never_the_token():
    token = generate_token()
    assert hash_token(token) == hash_token(token)
    assert len(hash_token(token)) == 64
    assert token not in hash_token(token)
    assert hash_token("a") != hash_token("b")


def test_codes_use_only_unambiguous_characters():
    for _ in range(200):
        code = generate_code()
        assert len(code) == CODE_LENGTH
        assert set(code) <= set(CODE_ALPHABET)
    assert not set("0O1IL") & set(CODE_ALPHABET)


def test_codes_are_not_repeated():
    assert len({generate_code() for _ in range(200)}) == 200


@pytest.mark.parametrize("typed", ["ABCD-EFGH", "abcd-efgh", " abcd efgh ", "ABCDEFGH", "ab-cd-ef-gh", "ABCD_EFGH"])
def test_normalize_code_tolerates_hyphens_spaces_and_case(typed):
    assert normalize_code(typed) == "ABCDEFGH"


@pytest.mark.parametrize("typed", [None, "", "   ", "-- --"])
def test_normalize_code_of_nothing_is_empty(typed):
    assert normalize_code(typed) == ""


def test_format_code_splits_in_the_middle():
    assert format_code("ABCDEFGH") == "ABCD-EFGH"
    assert normalize_code(format_code("ABCDEFGH")) == "ABCDEFGH"


# --- Propósito e código ---

@pytest.mark.parametrize("purpose, requires", [
    (InvitationPurpose.ACTIVATION, True),
    (InvitationPurpose.ADMIN_RESET, True),
    (InvitationPurpose.RECOVERY, False),
])
def test_only_recovery_goes_without_a_code(purpose, requires):
    assert purpose.requires_code is requires
    assert _invitation(purpose).requires_code is requires


@pytest.mark.parametrize("purpose", [InvitationPurpose.ACTIVATION, InvitationPurpose.ADMIN_RESET])
def test_invitation_with_code_needs_the_code_hash(purpose):
    with pytest.raises(ValueError, match="precisa do hash do código"):
        _invitation(purpose, code_hash=None)


def test_recovery_invitation_cannot_carry_a_code():
    with pytest.raises(ValueError, match="não tem código"):
        _invitation(InvitationPurpose.RECOVERY, code_hash="x")


# --- Validade ---

def test_fresh_invitation_is_usable():
    assert _invitation().is_usable(NOW, max_attempts=5) is True


def test_invitation_expires_exactly_at_the_deadline():
    invitation = _invitation(expires_at=NOW + timedelta(minutes=15))
    assert invitation.is_usable(NOW + timedelta(minutes=14, seconds=59), 5) is True
    assert invitation.is_usable(NOW + timedelta(minutes=15), 5) is False
    assert invitation.is_usable(NOW + timedelta(days=30), 5) is False


def test_consumed_invitation_is_not_usable():
    assert _invitation(consumed_at=NOW).is_usable(NOW, 5) is False


def test_revoked_invitation_is_not_usable():
    assert _invitation(revoked_at=NOW).is_usable(NOW, 5) is False


@pytest.mark.parametrize("attempts, usable", [(0, True), (4, True), (5, False), (6, False), (99, False)])
def test_invitation_locks_when_the_attempts_reach_the_limit(attempts, usable):
    assert _invitation(attempts=attempts).is_usable(NOW, max_attempts=5) is usable


def test_ensure_usable_raises_the_generic_error():
    with pytest.raises(AuthenticationFailedError, match="inválido, expirado ou já utilizado"):
        _invitation(consumed_at=NOW).ensure_usable(NOW, 5)
    _invitation().ensure_usable(NOW, 5)


def test_invitation_gets_its_own_id():
    assert _invitation().id != _invitation().id
