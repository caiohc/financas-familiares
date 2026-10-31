from abc import ABC, abstractmethod


class AbstractPasswordHasher(ABC):
    """Porta para o hash de senhas: o algoritmo é detalhe de infraestrutura."""

    @abstractmethod
    def hash(self, password: str) -> str:
        pass

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool:
        pass
