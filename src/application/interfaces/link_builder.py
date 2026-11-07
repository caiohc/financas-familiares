from abc import ABC, abstractmethod


class AbstractLinkBuilder(ABC):
    """Porta que monta os links enviados por e-mail. A aplicação não conhece URLs nem o Flask."""

    @abstractmethod
    def invitation_link(self, token: str) -> str:
        """Página em que a pessoa define a senha (ativação ou redefinição), com o código recebido por outro canal."""
        pass

    @abstractmethod
    def recovery_link(self, token: str) -> str:
        """Página em que a pessoa escolhe nova senha (recuperação por e-mail, sem código)."""
        pass
