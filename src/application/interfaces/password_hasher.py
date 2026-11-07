import secrets
from abc import ABC, abstractmethod


class AbstractPasswordHasher(ABC):
    """Porta para o hash de senhas: o algoritmo é detalhe de infraestrutura."""

    @abstractmethod
    def hash(self, password: str) -> str:
        pass

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool:
        pass

    def needs_rehash(self, password_hash: str) -> bool:
        """True se o hash foi gerado com um algoritmo ou parâmetros antigos e deve ser regravado no próximo login."""
        return False

    def dummy_hash(self) -> str:
        """Hash de uma senha que ninguém conhece, calculado uma vez.

        Quando o usuário não existe, o login confere a senha contra este hash para gastar o mesmo
        tempo de um usuário real: o tempo de resposta não revela quais usuários existem.
        """
        if getattr(self, "_dummy_hash", None) is None:
            self._dummy_hash = self.hash(secrets.token_urlsafe(24))
        return self._dummy_hash
