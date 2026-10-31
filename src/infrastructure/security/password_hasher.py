from werkzeug.security import check_password_hash, generate_password_hash

from application.interfaces.password_hasher import AbstractPasswordHasher


class WerkzeugPasswordHasher(AbstractPasswordHasher):
    """Hash com salt (scrypt, o padrão do Werkzeug que já acompanha o Flask)."""

    def hash(self, password: str) -> str:
        return generate_password_hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return check_password_hash(password_hash, password)
