import uuid
from datetime import datetime
from typing import Callable, Optional

from application.dtos.identity_dtos import (
    CreateRootDTO,
    CreateUserDTO,
    InvitationIssuedDTO,
    UpdateUserDTO,
    UserResponseDTO,
)
from application.dtos.shared_dtos import DEFAULT_PAGE_SIZE, DeletionPreviewDTO, PageDTO
from application.interfaces.password_hasher import AbstractPasswordHasher
from application.interfaces.unit_of_work import AbstractUnitOfWork
from application.services.access_manager import AccessManager
from application.services.pagination import build_page
from domain.family.exceptions import family_not_found
from domain.identity import policy
from domain.identity.entities import Role, User
from domain.identity.exceptions import (
    access_already_defined,
    access_denied,
    account_deactivated,
    cannot_act_on_self,
    email_already_exists,
    email_in_use,
    email_unchanged,
    root_already_exists,
    root_cannot_be_created,
    root_cannot_be_deleted,
    root_not_found,
    user_has_dependencies,
    user_not_found,
    username_already_exists,
    username_in_use,
)
from domain.identity.invitations import InvitationPurpose
from domain.identity.policy import Principal
from domain.shared.clock import utcnow


class UserService:
    """
    Orquestra as operações de negócio de usuário.
    Sem nenhum acoplamento com Web, HTTP ou SQL.

    Toda operação sobre contas recebe QUEM está agindo (`actor`, um Principal vindo da sessão) e confere
    a política (domain/identity/policy.py). Para quem não pode ver um usuário (outra família), ele
    simplesmente não existe (404); para quem vê mas não pode agir, é 403.
    """

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        password_hasher: AbstractPasswordHasher,
        access_manager: AccessManager,
        clock: Callable[[], datetime] = utcnow,
    ):
        self.uow = uow
        self.password_hasher = password_hasher
        self.access_manager = access_manager
        self.clock = clock

    @staticmethod
    def _to_dto(user: User) -> UserResponseDTO:
        return UserResponseDTO(
            id=user.id,
            role=user.role,
            family_id=user.family_id,
            name=user.name,
            username=user.username,
            email=user.email,
            status=user.status,
            is_active=user.is_active,
            is_pending=user.is_pending,
        )

    # --- Usuário root (CLI) ---

    def get_root(self) -> Optional[UserResponseDTO]:
        """O usuário root, se já existir (consulta da CLI, que roda no servidor, sem ator)."""
        with self.uow:
            root = self.uow.users.get_by_role(Role.ROOT)
            return self._to_dto(root) if root else None

    def check_root_username(self, username: Optional[str]) -> str:
        """Valida o nome de usuário do root e confere que está livre. Devolve o nome normalizado."""
        name = User.normalize_username(username)
        with self.uow:
            if self.uow.users.get_by_username(name):
                raise username_in_use(name)
        return name

    def check_root_email(self, email: Optional[str], ignore_user_id: Optional[uuid.UUID] = None) -> str:
        """Valida o e-mail do root e confere que está livre (exceto para a própria conta, em `ignore_user_id`).
        Devolve o e-mail normalizado."""
        address = User.normalize_email(email)
        with self.uow:
            owner = self.uow.users.get_by_email(address)
            if owner and owner.id != ignore_user_id:
                raise email_in_use(address)
        return address

    def create_root(self, dto: CreateRootDTO) -> UserResponseDTO:
        """
        Resolve o "ovo e a galinha": cria o usuário root, o inicial da aplicação, que não representa uma
        pessoa (sem nome). Quem executa a CLI tem acesso ao servidor e escolhe a senha ali mesmo.
        Só funciona enquanto não existir um root; depois, é ele quem cadastra os administradores do sistema.
        """
        with self.uow:
            existing = self.uow.users.get_by_role(Role.ROOT)
            if existing:
                raise root_already_exists()

            username = User.normalize_username(dto.username)
            email = User.normalize_email(dto.email)
            password = User.validate_raw_password(dto.password)
            User.validate_password_confirmation(password, dto.password_confirmation)

            if self.uow.users.get_by_username(username):
                raise username_in_use(username)
            owner = self.uow.users.get_by_email(email)
            if owner:
                raise email_in_use(email)

            root = User(
                role=Role.ROOT,
                username=username,
                email=email,
                password_hash=self.password_hasher.hash(password),
                activated_at=self.clock(),
            )
            self.uow.users.save(root)
            self.uow.commit()
            return self._to_dto(root)

    def reset_root_password(self, password: Optional[str], password_confirmation: Optional[str]) -> UserResponseDTO:
        """Único caminho de redefinição da senha do root: a CLI, executada no servidor. O root não tem
        recuperação por e-mail e nenhum administrador age sobre ele."""
        with self.uow:
            root = self.uow.users.get_by_role(Role.ROOT)
            if root is None:
                raise root_not_found()
            new_password = User.validate_raw_password(password)
            User.validate_password_confirmation(new_password, password_confirmation)
            root.change_password(self.password_hasher.hash(new_password))
            root.reactivate()
            self.uow.users.save(root)
            self.uow.commit()
            return self._to_dto(root)

    def change_root_email(self, email: Optional[str], email_confirmation: Optional[str]) -> UserResponseDTO:
        """Troca o e-mail do root. Só pela CLI, executada no servidor: nenhum administrador altera o e-mail do root
        pela aplicação, e o root não tem recuperação por e-mail (o e-mail dele não serve de canal de recuperação)."""
        with self.uow:
            root = self.uow.users.get_by_role(Role.ROOT)
            if root is None:
                raise root_not_found()

            new_email = User.normalize_email(email)
            User.validate_email_confirmation(new_email, email_confirmation)
            if new_email.casefold() == root.email.casefold():
                raise email_unchanged()
            owner = self.uow.users.get_by_email(new_email)
            if owner and owner.id != root.id:
                raise email_in_use(new_email)

            root.change_email(new_email)
            self.uow.users.save(root)
            self.uow.commit()
            return self._to_dto(root)

    # --- Cadastro por um administrador ---

    def create_user(self, actor: Principal, dto: CreateUserDTO) -> InvitationIssuedDTO:
        """Cadastra uma conta PENDENTE (sem senha) e emite o convite de ativação. O administrador recebe o
        código para repassar por outro canal; o link segue por e-mail para o endereço informado."""
        with self.uow:
            self._require_manager(actor)

            role = User.validate_role(dto.role)
            if role is Role.ROOT:
                raise root_cannot_be_created()
            if not policy.can_create_user(actor, role, dto.family_id):
                raise access_denied("create_user")

            family_id = User.validate_family_for_role(role, dto.family_id)
            if family_id is not None and not self.uow.families.get_by_id(family_id):
                raise family_not_found(family_id)

            username = User.normalize_username(dto.username)
            email = User.normalize_email(dto.email)
            User.validate_email_confirmation(email, dto.email_confirmation)
            name = User.normalize_name(dto.name, role)

            if self.uow.users.get_by_username(username):
                raise username_already_exists(username)
            if self.uow.users.get_by_email(email):
                raise email_already_exists(email)

            user = User(role=role, family_id=family_id, name=name, username=username, email=email)
            self.uow.users.save(user)
            issued = self.access_manager.issue(self.uow, user, InvitationPurpose.ACTIVATION, actor.user_id)
            self.uow.commit()
            result = self._issued_dto(user, issued)
        result.email_sent = self.access_manager.deliver_invitation(issued, user)
        return result

    def issue_invitation(self, actor: Principal, user_id: uuid.UUID) -> InvitationIssuedDTO:
        """Reenvia a ativação de uma conta pendente ou, para um administrador do sistema, redefine a senha.
        Revoga o convite anterior. Usuário de família que já ativou a conta redefine a senha por conta
        própria ("Esqueci minha senha"): não há convite do administrador para ele."""
        with self.uow:
            self._require_manager(actor)
            user = self._get_visible(actor, user_id)
            if not policy.can_issue_invitation(actor, user):
                raise access_denied("issue_invitation")
            if not user.is_active:
                raise account_deactivated()

            if user.is_pending:
                purpose = InvitationPurpose.ACTIVATION
            elif user.is_system_admin:
                purpose = InvitationPurpose.ADMIN_RESET
                # A senha atual deixa de valer já: o convite é a única forma de entrar de novo.
                user.revoke_password()
                self.uow.users.save(user)
            else:
                raise access_already_defined()

            issued = self.access_manager.issue(self.uow, user, purpose, actor.user_id)
            self.uow.commit()
            result = self._issued_dto(user, issued)
        result.email_sent = self.access_manager.deliver_invitation(issued, user)
        return result

    @staticmethod
    def _issued_dto(user: User, issued) -> InvitationIssuedDTO:
        return InvitationIssuedDTO(
            user=UserService._to_dto(user),
            purpose=issued.invitation.purpose,
            code=issued.code,
            expires_at=issued.invitation.expires_at,
            email_sent=False,
        )

    # --- Consulta ---

    def get_user(self, actor: Principal, user_id: uuid.UUID) -> UserResponseDTO:
        with self.uow:
            self._require_manager(actor)
            return self._to_dto(self._get_visible(actor, user_id))

    def list_users_page(
        self, actor: Principal, page: Optional[int] = 1, page_size: Optional[int] = DEFAULT_PAGE_SIZE,
        sort_by: Optional[str] = None, sort_dir: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PageDTO[UserResponseDTO]:
        with self.uow:
            self._require_manager(actor)
            # O administrador de família só enxerga a própria família (escopo do tenant, no repositório).
            family_scope = actor.family_id if actor.role is Role.FAMILY_ADMIN else None

            def fetch(number, size, field, descending, term):
                return self.uow.users.list_page(number, size, field, descending, term, family_id=family_scope)

            return build_page(
                fetch, self._to_dto, page, page_size, sort_by, sort_dir, ("name", "username", "email"), search,
            )

    # --- Edição, situação e exclusão ---

    def update_user(self, actor: Principal, user_id: uuid.UUID, dto: UpdateUserDTO) -> UserResponseDTO:
        with self.uow:
            user = self._get_manageable(actor, user_id, "update_user")

            # Valida tudo antes de alterar a entidade, para não deixá-la pela metade.
            username = User.normalize_username(dto.username)
            email = User.normalize_email(dto.email)
            User.normalize_name(dto.name, user.role)

            same_username = self.uow.users.get_by_username(username)
            if same_username and same_username.id != user_id:
                raise username_already_exists(username)
            same_email = self.uow.users.get_by_email(email)
            if same_email and same_email.id != user_id:
                raise email_already_exists(email)

            user.update_profile(dto.name, username, email)
            self.uow.users.save(user)
            self.uow.commit()
            return self._to_dto(user)

    def deactivate_user(self, actor: Principal, user_id: uuid.UUID) -> UserResponseDTO:
        with self.uow:
            user = self._get_manageable(actor, user_id, "deactivate_user")
            if user.id == actor.user_id:
                raise cannot_act_on_self("desativar")
            user.deactivate()
            self.uow.users.save(user)
            self.uow.commit()
            return self._to_dto(user)

    def reactivate_user(self, actor: Principal, user_id: uuid.UUID) -> UserResponseDTO:
        with self.uow:
            user = self._get_manageable(actor, user_id, "reactivate_user")
            user.reactivate()
            self.uow.users.save(user)
            self.uow.commit()
            return self._to_dto(user)

    def preview_user_deletion(self, actor: Principal, user_id: uuid.UUID) -> DeletionPreviewDTO:
        """Antecipa, para a tela de confirmação, se a exclusão será bloqueada e por quê."""
        with self.uow:
            self._require_manager(actor)
            user = self._get_visible(actor, user_id)
            if user.is_root:
                return DeletionPreviewDTO(name=user.username, blocked_reason=str(root_cannot_be_deleted(user.id)))
            if not policy.can_manage_user(actor, user):
                raise access_denied("delete_user")

            reason = None
            if user.id == actor.user_id:
                reason = str(cannot_act_on_self("excluir"))
            elif self.uow.users.has_dependencies(user.id):
                reason = str(user_has_dependencies(user.id))
            return DeletionPreviewDTO(name=user.name or user.username, blocked_reason=reason)

    def delete_user(self, actor: Principal, user_id: uuid.UUID) -> None:
        with self.uow:
            self._require_manager(actor)
            user = self._get_visible(actor, user_id)
            if user.is_root:
                raise root_cannot_be_deleted(user_id)
            if not policy.can_manage_user(actor, user):
                raise access_denied("delete_user")
            if user.id == actor.user_id:
                raise cannot_act_on_self("excluir")

            # Os convites do usuário saem junto; se houver outra dependência, a exceção desfaz tudo.
            self.uow.invitations.delete_for_user(user_id)
            if self.uow.users.has_dependencies(user_id):
                raise user_has_dependencies(user_id)

            self.uow.users.delete(user_id)
            self.uow.commit()

    # --- Internos ---

    @staticmethod
    def _require_manager(actor: Principal) -> None:
        if not policy.can_manage_users(actor):
            raise access_denied("manage_users")

    def _get_visible(self, actor: Principal, user_id: uuid.UUID) -> User:
        """Usuário que o ator pode ver; para os demais (inclusive de outra família), ele não existe."""
        user = self.uow.users.get_by_id(user_id)
        if user is None or not policy.can_view_user(actor, user):
            raise user_not_found(user_id)
        return user

    def _get_manageable(self, actor: Principal, user_id: uuid.UUID, action: str) -> User:
        self._require_manager(actor)
        user = self._get_visible(actor, user_id)
        if not policy.can_manage_user(actor, user):
            raise access_denied(action)
        return user
