from infrastructure.security.password_hasher import WerkzeugPasswordHasher


def test_hash_is_not_the_plain_password_and_verifies():
    hasher = WerkzeugPasswordHasher()
    password_hash = hasher.hash("senha-temporaria")

    assert password_hash != "senha-temporaria"
    assert hasher.verify("senha-temporaria", password_hash) is True
    assert hasher.verify("outra-senha", password_hash) is False


def test_hash_is_salted():
    hasher = WerkzeugPasswordHasher()
    assert hasher.hash("senha-temporaria") != hasher.hash("senha-temporaria")
