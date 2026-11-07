import hashlib
import hmac
import uuid
from datetime import datetime
from typing import Callable, Optional

from application.dtos.identity_dtos import SessionUserDTO
from application.interfaces.password_hasher import AbstractPasswordHasher
from application.interfaces.unit_of_work import AbstractUnitOfWork
from application.services.access_manager import AccessManager
from domain.identity.entities import User
from domain.identity.exceptions import (
    invalid_credentials,
    invalid_current_password,
    new_password_same_as_current,
    user_not_found,
)
from domain.shared.clock import utcnow


class AuthService:
    """
    Autenticação: login, carregamento do usuário da sessão e troca da própria senha.
    Sem nenhum acoplamento com Web, HTTP ou SQL.
    """

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        password_hasher: AbstractPasswordHasher,
        access_manager: AccessManager,
        secret_key: str,
        clock: Callable[[], datetime] = utcnow,
    ):
        self.uow = uow
        self.hasher = password_hasher
        self.access_manager = access_manager
        self._secret_key = secret_key.encode("utf-8")
        self.clock = clock

    # --- Sessão ---

    def _credential_version(self, user: User) -> str:
        """Impressão digital da senha atual, assinada com a SECRET_KEY. Trocar ou revogar a senha muda
        a impressão e derruba todas as sessões abertas, sem precisar guardar sessões no servidor."""
        return hmac.new(self._secret_key, (user.password_hash or "").encode("utf-8"), hashlib.sha256).hexdigest()[:32]

    def _to_session_dto(self, user: User) -> SessionUserDTO:
        return SessionUserDTO(
            id=user.id,
            role=user.role,
            family_id=user.family_id,
            name=user.name,
            username=user.username,
            email=user.email,
            session_id=f"{user.id}:{self._credential_version(user)}",
        )

    def load_session_user(self, session_id: Optional[str]) -> Optional[SessionUserDTO]:
        """Usuário de um cookie de sessão, ou None se a sessão não vale mais: usuário excluído,
        desativado, sem senha, ou senha trocada desde o login. Recarrega do banco a cada requisição."""
        user_id, separator, version = (session_id or "").partition(":")
        if not separator:
            return None
        try:
            parsed_id = uuid.UUID(user_id)
        except ValueError:
            return None
        with self.uow:
            user = self.uow.users.get_by_id(parsed_id)
            if user is None or not user.can_authenticate:
                return None
            if not hmac.compare_digest(version, self._credential_version(user)):
                return None
            return self._to_session_dto(user)

    def find_session_user_by_username(self, username: str) -> Optional[SessionUserDTO]:
        """Só para o usuário de desenvolvimento (AUTH_ENABLED=false): sem conferir senha."""
        with self.uow:
            user = self.uow.users.get_by_username((username or "").strip())
            if user is None or not user.can_authenticate:
                return None
            return self._to_session_dto(user)

    # --- Login ---

    def authenticate(self, identifier: Optional[str], password: Optional[str]) -> SessionUserDTO:
        """Confere usuário (ou e-mail) e senha. Qualquer falha devolve a MESMA mensagem genérica."""
        identifier = (identifier or "").strip()
        with self.uow:
            user = self.uow.users.get_by_username(identifier) or self.uow.users.get_by_email(identifier)
            has_password = user is not None and user.password_hash is not None
            # Sempre há um hash para conferir (o falso, se não houver usuário): o tempo não denuncia.
            stored = user.password_hash if has_password else self.hasher.dummy_hash()
            password_matches = self.hasher.verify(password or "", stored)

            if not (user is not None and has_password and password_matches and user.can_authenticate):
                raise invalid_credentials()

            if self.hasher.needs_rehash(user.password_hash):
                user.change_password(self.hasher.hash(password))
                self.uow.users.save(user)
                self.uow.commit()
            return self._to_session_dto(user)

    # --- Troca da própria senha ---

    def change_own_password(
        self, user_id: uuid.UUID, current_password: Optional[str], new_password: Optional[str],
        new_password_confirmation: Optional[str],
    ) -> SessionUserDTO:
        """Pede a senha atual (uma sessão roubada não basta). Devolve a sessão renovada do próprio usuário:
        todas as OUTRAS sessões abertas caem."""
        with self.uow:
            user = self.uow.users.get_by_id(user_id)
            if user is None or not user.can_authenticate:
                raise user_not_found(user_id)

            if not self.hasher.verify(current_password or "", user.password_hash):
                raise invalid_current_password()

            password = User.validate_raw_password(new_password)
            User.validate_password_confirmation(password, new_password_confirmation)
            if password == current_password:
                raise new_password_same_as_current()

            user.change_password(self.hasher.hash(password))
            self.uow.users.save(user)
            # Um link de recuperação enviado antes não pode sobreviver à troca da senha.
            self.uow.invitations.revoke_active_for_user(user.id, self.clock())
            self.uow.commit()
            session_user = self._to_session_dto(user)
            notify = user
        self.access_manager.notify_password_changed(notify)
        return session_user
