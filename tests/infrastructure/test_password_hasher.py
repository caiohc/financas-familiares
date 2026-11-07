import pytest
from werkzeug.security import generate_password_hash

from infrastructure.security.password_hasher import Argon2PasswordHasher


@pytest.fixture(scope="module")
def hasher():
    return Argon2PasswordHasher("test")


def test_hash_is_argon2id_and_is_not_the_plain_password(hasher):
    password_hash = hasher.hash("senha-temporaria")

    assert password_hash.startswith("$argon2id$")
    assert "senha-temporaria" not in password_hash


def test_hash_verifies_the_right_password_and_only_it(hasher):
    password_hash = hasher.hash("senha-temporaria")

    assert hasher.verify("senha-temporaria", password_hash) is True
    for wrong in ("outra-senha", "Senha-Temporaria", "senha-temporaria ", " senha-temporaria", ""):
        assert hasher.verify(wrong, password_hash) is False


def test_hash_is_salted(hasher):
    assert hasher.hash("senha-temporaria") != hasher.hash("senha-temporaria")


@pytest.mark.parametrize("password", ["a", "çãõ-ÀÉÎ-123", "senha com espaços", "x" * 500, "🔒 cadeado 🔑", "\u0000nul"])
def test_unusual_passwords_round_trip(hasher, password):
    assert hasher.verify(password, hasher.hash(password)) is True


@pytest.mark.parametrize("garbage", ["", "x", "$argon2id$", "$argon2id$v=19$m=1,t=1,p=1$bad$bad", "scrypt:inexistente$a$b", "$2b$12$abc"])
def test_verify_with_a_garbage_stored_hash_is_false_and_never_raises(hasher, garbage):
    assert hasher.verify("qualquer-senha", garbage) is False


# --- Hashes antigos (scrypt/PBKDF2 do Werkzeug) continuam valendo e são regravados ---

def test_legacy_werkzeug_hashes_still_verify(hasher):
    legacy = generate_password_hash("senha-antiga")

    assert hasher.verify("senha-antiga", legacy) is True
    assert hasher.verify("senha-errada", legacy) is False


def test_legacy_hashes_are_marked_for_rehash_and_argon2_ones_are_not(hasher):
    assert hasher.needs_rehash(generate_password_hash("x")) is True
    assert hasher.needs_rehash(hasher.hash("x")) is False


def test_a_hash_made_with_weaker_parameters_needs_rehash():
    strong = Argon2PasswordHasher("default")
    weak_hash = Argon2PasswordHasher("test").hash("x")

    assert strong.needs_rehash(weak_hash) is True


# --- Hash falso do login ---

def test_dummy_hash_is_valid_computed_once_and_matches_no_ordinary_password(hasher):
    first = hasher.dummy_hash()

    assert first == hasher.dummy_hash()
    assert first.startswith("$argon2id$")
    for guess in ("", "password", "senha", "12345678", "admin"):
        assert hasher.verify(guess, first) is False


def test_dummy_hash_differs_between_hasher_instances():
    assert Argon2PasswordHasher("test").dummy_hash() != Argon2PasswordHasher("test").dummy_hash()
