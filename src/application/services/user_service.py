import uuid
from typing import Optional

from application.dtos.identity_dtos import CreateRootDTO, CreateUserDTO, UpdateUserDTO, UserResponseDTO
from application.dtos.shared_dtos import DEFAULT_PAGE_SIZE, DeletionPreviewDTO, PageDTO
from application.interfaces.password_hasher import AbstractPasswordHasher
from application.interfaces.unit_of_work import AbstractUnitOfWork
from application.services.pagination import build_page
from domain.family.exceptions import family_not_found
from domain.identity.entities import Role, User
from domain.identity.exceptions import (
    email_already_exists,
    root_already_exists,
    root_cannot_be_created,
    root_cannot_be_deleted,
    user_has_dependencies,
    user_not_found,
    username_already_exists,
)


class UserService:
    """
    Orquestra as operações de negócio de usuário.
    Sem nenhum acoplamento com Web, HTTP ou SQL.
    """
    def __init__(self, uow: AbstractUnitOfWork, password_hasher: AbstractPasswordHasher):
        self.uow = uow
        self.password_hasher = password_hasher

    def _to_dto(self, user: User) -> UserResponseDTO:
        return UserResponseDTO(
            id=user.id,
            role=user.role,
            family_id=user.family_id,
            name=user.name,
            username=user.username,
            email=user.email,
            must_change_password=user.must_change_password,
        )

    def create_root(self, dto: CreateRootDTO) -> UserResponseDTO:
        """
        Resolve o "ovo e a galinha": cria o usuário root, o inicial da aplicação, que não
        representa uma pessoa (sem nome). Tem senha temporária (troca obrigatória no
        primeiro acesso). Só funciona enquanto não existir um root; depois, é ele quem
        cadastra os administradores do sistema, que são pessoas identificadas.
        """
        with self.uow:
            if self.uow.users.exists_with_role(Role.ROOT):
                raise root_already_exists()

            username = User.normalize_username(dto.username)
            email = User.normalize_email(dto.email)
            password = User.validate_raw_password(dto.temporary_password)

            if self.uow.users.get_by_username(username):
                raise username_already_exists(username)
            if self.uow.users.get_by_email(email):
                raise email_already_exists(email)

            root = User(
                role=Role.ROOT,
                username=username,
                email=email,
                password_hash=self.password_hasher.hash(password),
                must_change_password=True,
            )
            self.uow.users.save(root)
            self.uow.commit()
            return self._to_dto(root)

    def create_user(self, dto: CreateUserDTO) -> UserResponseDTO:
        """Cadastro por um administrador: senha temporária, com troca obrigatória no primeiro acesso."""
        with self.uow:
            role = User.validate_role(dto.role)
            if role is Role.ROOT:
                raise root_cannot_be_created()
            # Valida a combinação papel/família antes de consultar o banco.
            family_id = User.validate_family_for_role(role, dto.family_id)
            if family_id is not None and not self.uow.families.get_by_id(family_id):
                raise family_not_found(family_id)

            username = User.normalize_username(dto.username)
            email = User.normalize_email(dto.email)
            name = User.normalize_name(dto.name, role)
            password = User.validate_raw_password(dto.temporary_password)

            if self.uow.users.get_by_username(username):
                raise username_already_exists(username)
            if self.uow.users.get_by_email(email):
                raise email_already_exists(email)

            user = User(
                role=role,
                family_id=family_id,
                name=name,
                username=username,
                email=email,
                password_hash=self.password_hasher.hash(password),
                must_change_password=True,
            )
            self.uow.users.save(user)
            self.uow.commit()
            return self._to_dto(user)

    def get_user(self, user_id: uuid.UUID) -> UserResponseDTO:
        with self.uow:
            user = self.uow.users.get_by_id(user_id)
            if not user:
                raise user_not_found(user_id)
            return self._to_dto(user)

    def list_users_page(
        self, page: Optional[int] = 1, page_size: Optional[int] = DEFAULT_PAGE_SIZE,
        sort_by: Optional[str] = None, sort_dir: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PageDTO[UserResponseDTO]:
        with self.uow:
            return build_page(
                self.uow.users.list_page, self._to_dto, page, page_size, sort_by, sort_dir,
                ("name", "username", "email"), search,
            )

    def update_user(self, user_id: uuid.UUID, dto: UpdateUserDTO) -> UserResponseDTO:
        with self.uow:
            user = self.uow.users.get_by_id(user_id)
            if not user:
                raise user_not_found(user_id)

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

    def preview_user_deletion(self, user_id: uuid.UUID) -> DeletionPreviewDTO:
        """Antecipa, para a tela de confirmação, se a exclusão será bloqueada e por quê."""
        with self.uow:
            user = self.uow.users.get_by_id(user_id)
            if not user:
                raise user_not_found(user_id)

            return DeletionPreviewDTO(name=user.name or user.username, blocked_reason=self._deletion_block(user))

    def delete_user(self, user_id: uuid.UUID) -> None:
        with self.uow:
            user = self.uow.users.get_by_id(user_id)
            if not user:
                raise user_not_found(user_id)

            if user.is_root:
                raise root_cannot_be_deleted(user_id)
            if self.uow.users.has_dependencies(user_id):
                raise user_has_dependencies(user_id)

            self.uow.users.delete(user_id)
            self.uow.commit()

    def _deletion_block(self, user: User) -> Optional[str]:
        if user.is_root:
            return str(root_cannot_be_deleted(user.id))
        if self.uow.users.has_dependencies(user.id):
            return str(user_has_dependencies(user.id))
        return None
