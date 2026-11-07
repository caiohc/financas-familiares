from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from werkzeug.security import check_password_hash

from application.interfaces.password_hasher import AbstractPasswordHasher

# Perfil leve, só para testes: os parâmetros padrão (64 MiB, 3 iterações) deixariam a suíte lenta.
_TEST_PROFILE = dict(time_cost=1, memory_cost=8, parallelism=1)


class Argon2PasswordHasher(AbstractPasswordHasher):
    """Argon2id (primeira recomendação do OWASP), com os parâmetros padrão da biblioteca.

    Hashes anteriores à troca (scrypt/PBKDF2 do Werkzeug) continuam sendo aceitos na conferência
    e são marcados para regravação: no próximo login bem-sucedido viram Argon2id.
    """

    def __init__(self, profile: str = "default"):
        self._hasher = PasswordHasher(**_TEST_PROFILE) if profile == "test" else PasswordHasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        if password_hash.startswith("$argon2"):
            try:
                return self._hasher.verify(password_hash, password)
            except (VerificationError, InvalidHashError):
                return False
        # Legado (formato "método$sal$hash" do Werkzeug). Um hash corrompido ou de método desconhecido
        # nunca pode virar erro no login (500): vale como senha que não confere.
        try:
            return check_password_hash(password_hash, password)
        except ValueError:
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        if not password_hash.startswith("$argon2"):
            return True
        return self._hasher.check_needs_rehash(password_hash)
