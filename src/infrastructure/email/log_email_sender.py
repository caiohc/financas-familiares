import logging

from application.interfaces.email_sender import AbstractEmailSender

logger = logging.getLogger("financas.email")


class LogEmailSender(AbstractEmailSender):
    """Só para DESENVOLVIMENTO: escreve a mensagem no log em vez de enviá-la.

    A mensagem traz o link com o token, então este backend é proibido em produção (ver security_config.py).
    """

    def send(self, to: str, subject: str, body: str) -> None:
        logger.warning("[E-MAIL DE DESENVOLVIMENTO] Para: %s | Assunto: %s\n%s", to, subject, body)
