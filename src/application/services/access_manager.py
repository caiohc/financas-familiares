import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from application import notifications
from application.interfaces.email_sender import AbstractEmailSender, EmailDeliveryError
from application.interfaces.link_builder import AbstractLinkBuilder
from application.interfaces.password_hasher import AbstractPasswordHasher
from application.interfaces.unit_of_work import AbstractUnitOfWork
from application.security_settings import SecuritySettings
from domain.identity.entities import User
from domain.identity.invitations import (
    Invitation,
    InvitationPurpose,
    format_code,
    generate_code,
    generate_token,
    hash_token,
)
from domain.shared.clock import utcnow

logger = logging.getLogger(__name__)


@dataclass
class IssuedInvitation:
    invitation: Invitation
    token: str                 # só existe aqui e no e-mail; o banco guarda apenas o hash
    code: Optional[str]        # idem; formatado para ser lido ao telefone (ex.: ABCD-EFGH)


class AccessManager:
    """
    Emite convites e envia as mensagens de segurança.

    Não abre transação: quem emite chama `issue` dentro do `with uow` do próprio caso de uso, para
    que usuário, revogação do convite anterior e convite novo sejam gravados juntos. O envio de
    e-mail acontece DEPOIS do commit (`deliver_*`) e uma falha de entrega nunca desfaz o que foi
    gravado: o convite continua válido e o administrador pode reenviá-lo.
    """

    def __init__(
        self,
        hasher: AbstractPasswordHasher,
        email_sender: AbstractEmailSender,
        link_builder: AbstractLinkBuilder,
        settings: SecuritySettings,
        clock: Callable[[], datetime] = utcnow,
    ):
        self.hasher = hasher
        self.email_sender = email_sender
        self.link_builder = link_builder
        self.settings = settings
        self.clock = clock

    def issue(
        self, uow: AbstractUnitOfWork, user: User, purpose: InvitationPurpose, created_by_user_id=None,
    ) -> IssuedInvitation:
        now = self.clock()
        # Um convite ativo por usuário: emitir outro revoga o anterior (o link antigo morre).
        uow.invitations.revoke_active_for_user(user.id, now)

        token = generate_token()
        code = generate_code() if purpose.requires_code else None
        ttl = self.settings.recovery_ttl if purpose is InvitationPurpose.RECOVERY else self.settings.invitation_ttl
        invitation = Invitation(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(token),
            code_hash=self.hasher.hash(code) if code else None,
            created_by_user_id=created_by_user_id,
            created_at=now,
            expires_at=now + ttl,
        )
        uow.invitations.save(invitation)
        return IssuedInvitation(invitation=invitation, token=token, code=format_code(code) if code else None)

    def deliver_invitation(self, issued: IssuedInvitation, user: User) -> bool:
        reset = issued.invitation.purpose is InvitationPurpose.ADMIN_RESET
        subject, body = notifications.invitation_email(
            name=user.name or user.username,
            link=self.link_builder.invitation_link(issued.token),
            valid_for_hours=int(self.settings.invitation_ttl.total_seconds() // 3600),
            reset=reset,
        )
        return self._send(user.email, subject, body)

    def deliver_recovery(self, issued: IssuedInvitation, user: User) -> bool:
        subject, body = notifications.recovery_email(
            link=self.link_builder.recovery_link(issued.token),
            valid_for_minutes=int(self.settings.recovery_ttl.total_seconds() // 60),
        )
        return self._send(user.email, subject, body)

    def notify_password_changed(self, user: User) -> bool:
        subject, body = notifications.password_changed_email(name=user.name)
        return self._send(user.email, subject, body)

    def _send(self, to: str, subject: str, body: str) -> bool:
        try:
            self.email_sender.send(to, subject, body)
            return True
        except EmailDeliveryError:
            # Sem o corpo na mensagem: ele traz o link com o token.
            logger.exception("Falha ao enviar e-mail de segurança (assunto: %s).", subject)
            return False
