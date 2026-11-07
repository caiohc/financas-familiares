from abc import ABC, abstractmethod


class EmailDeliveryError(Exception):
    """Falha ao entregar um e-mail ao servidor de saída."""


class AbstractEmailSender(ABC):
    """Porta para o envio de e-mail: o provedor (SMTP, serviço de e-mail, log) é detalhe de infraestrutura."""

    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None:
        """Envia uma mensagem de texto. Levanta EmailDeliveryError se não conseguir entregar."""
        pass
