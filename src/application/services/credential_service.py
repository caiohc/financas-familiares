from datetime import datetime
from typing import Callable, Optional

from application.dtos.identity_dtos import InvitationInfoDTO
from application.interfaces.password_hasher import AbstractPasswordHasher
from application.interfaces.unit_of_work import AbstractUnitOfWork
from application.security_settings import SecuritySettings
from application.services.access_manager import AccessManager
from domain.identity.entities import Role, User
from domain.identity.exceptions import invalid_invitation, invalid_recovery_link
from domain.identity.invitations import Invitation, InvitationPurpose, hash_token, normalize_code
from domain.shared.clock import utcnow
from domain.shared.exceptions import AuthenticationFailedError

SET_PASSWORD_PURPOSES = (InvitationPurpose.ACTIVATION, InvitationPurpose.ADMIN_RESET)

# A recuperação autônoma vale só para quem já passou pelo primeiro acesso e não é de nível de sistema:
# administradores do sistema e o root têm fluxos mais rígidos (convite com código / CLI).
SELF_RECOVERY_ROLES = (Role.FAMILY_ADMIN, Role.FAMILY_USER)


class CredentialService:
    """
    Definição de senha pelos convites (ativação e redefinição de administrador do sistema, com link +
    código) e recuperação autônoma ("Esqueci minha senha", só link). Sem acoplamento com Web ou SQL.

    As falhas de convite têm sempre a mesma mensagem genérica: não revelam se o link existe, venceu,
    foi usado ou se o código é que estava errado.
    """

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        password_hasher: AbstractPasswordHasher,
        access_manager: AccessManager,
        settings: SecuritySettings,
        clock: Callable[[], datetime] = utcnow,
    ):
        self.uow = uow
        self.hasher = password_hasher
        self.access_manager = access_manager
        self.settings = settings
        self.clock = clock

    # --- Consulta (para exibir a página do link) ---

    def inspect_invitation(self, token: Optional[str], purposes: tuple[InvitationPurpose, ...]) -> InvitationInfoDTO:
        with self.uow:
            invitation = self._find_usable(token, purposes, invalid_invitation)
            self._require_account_for(invitation, self.uow.users.get_by_id(invitation.user_id), invalid_invitation)
            return InvitationInfoDTO(purpose=invitation.purpose, requires_code=invitation.requires_code)

    # --- Ativação e redefinição de administrador do sistema (link + código) ---

    def complete_invitation(
        self, token: Optional[str], code: Optional[str], password: Optional[str],
        password_confirmation: Optional[str],
    ) -> None:
        notify = None
        with self.uow:
            invitation = self._find_usable(token, SET_PASSWORD_PURPOSES, invalid_invitation)
            user = self.uow.users.get_by_id(invitation.user_id)
            self._require_account_for(invitation, user, invalid_invitation)

            # Erro de digitação da senha não gasta tentativa do código nem revela nada sobre ele.
            new_password = User.validate_raw_password(password)
            User.validate_password_confirmation(new_password, password_confirmation)

            if not self.hasher.verify(normalize_code(code), invitation.code_hash):
                # Grava a tentativa ANTES de falhar: sem o commit, o rollback da falha a apagaria.
                self.uow.invitations.register_failed_attempt(invitation.id)
                self.uow.commit()
                raise invalid_invitation()

            now = self.clock()
            if not self.uow.invitations.consume(invitation.id, now, self.settings.max_code_attempts):
                raise invalid_invitation()      # perdeu a corrida para outra requisição

            was_reset = invitation.purpose is InvitationPurpose.ADMIN_RESET
            user.define_password(self.hasher.hash(new_password), now)
            self.uow.users.save(user)
            self.uow.commit()
            notify = user if was_reset else None
        if notify is not None:
            self.access_manager.notify_password_changed(notify)

    # --- Recuperação autônoma ("Esqueci minha senha") ---

    def request_recovery(self, email: Optional[str]) -> None:
        """Resposta SEMPRE igual para quem pede: não confirma se o e-mail existe nem se a conta é elegível.
        Só envia o link se a conta for de família, ativada, com senha e ativa."""
        issued = None
        user = None
        with self.uow:
            user = self.uow.users.get_by_email((email or "").strip())
            if user is not None and self._eligible_for_self_recovery(user):
                issued = self.access_manager.issue(self.uow, user, InvitationPurpose.RECOVERY, created_by_user_id=None)
                self.uow.commit()
        if issued is not None:
            self.access_manager.deliver_recovery(issued, user)

    def inspect_recovery(self, token: Optional[str]) -> None:
        with self.uow:
            invitation = self._find_usable(token, (InvitationPurpose.RECOVERY,), invalid_recovery_link)
            user = self.uow.users.get_by_id(invitation.user_id)
            if user is None or not self._eligible_for_self_recovery(user):
                raise invalid_recovery_link()

    def complete_recovery(
        self, token: Optional[str], password: Optional[str], password_confirmation: Optional[str],
    ) -> None:
        with self.uow:
            invitation = self._find_usable(token, (InvitationPurpose.RECOVERY,), invalid_recovery_link)
            user = self.uow.users.get_by_id(invitation.user_id)
            if user is None or not self._eligible_for_self_recovery(user):
                raise invalid_recovery_link()

            new_password = User.validate_raw_password(password)
            User.validate_password_confirmation(new_password, password_confirmation)

            if not self.uow.invitations.consume(invitation.id, self.clock(), self.settings.max_code_attempts):
                raise invalid_recovery_link()

            user.change_password(self.hasher.hash(new_password))
            self.uow.users.save(user)
            self.uow.commit()
        self.access_manager.notify_password_changed(user)

    # --- Internos ---

    @staticmethod
    def _eligible_for_self_recovery(user: User) -> bool:
        return user.role in SELF_RECOVERY_ROLES and not user.is_pending and user.can_authenticate

    def _find_usable(
        self, token: Optional[str], purposes: tuple[InvitationPurpose, ...], failure: Callable[[], AuthenticationFailedError],
    ) -> Invitation:
        if not token:
            raise failure()
        invitation = self.uow.invitations.get_by_token_hash(hash_token(token))
        if invitation is None or invitation.purpose not in purposes:
            raise failure()
        if not invitation.is_usable(self.clock(), self.settings.max_code_attempts):
            raise failure()
        return invitation

    @staticmethod
    def _require_account_for(invitation: Invitation, user: Optional[User], failure) -> None:
        # Conta excluída ou desativada: o convite não vale mais.
        if user is None or not user.is_active:
            raise failure()
