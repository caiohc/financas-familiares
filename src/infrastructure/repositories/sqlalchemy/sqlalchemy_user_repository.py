import uuid
from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.identity.entities import Role, User
from domain.identity.exceptions import email_already_exists, username_already_exists
from domain.identity.repositories import UserRepository
from domain.shared.pagination import Page
from domain.shared.text import fold_text

from infrastructure.database.models import UserModel
from infrastructure.repositories.sqlalchemy.dependencies import has_dependent_rows


def _contains(column, term: str):
    """Condição "contém o trecho", sem caixa e sem acentos; %, _ e \\ do termo valem como texto."""
    escaped = fold_text(term).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return func.fold(column).like(f"%{escaped}%", escape="\\")


SORTABLE_FIELDS = ("name", "username", "email")


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: UserModel) -> User:
        return User(
            id=uuid.UUID(model.id),
            role=model.role,
            family_id=uuid.UUID(model.family_id) if model.family_id else None,
            name=model.name,
            username=model.username,
            email=model.email,
            password_hash=model.password_hash,
            must_change_password=model.must_change_password,
        )

    def _to_model(self, entity: User) -> UserModel:
        return UserModel(
            id=str(entity.id),
            role=entity.role,
            family_id=str(entity.family_id) if entity.family_id else None,
            name=entity.name,
            username=entity.username,
            email=entity.email,
            password_hash=entity.password_hash,
            must_change_password=entity.must_change_password,
        )

    def save(self, user: User) -> None:
        model = self._to_model(user)
        try:
            self.session.merge(model)
            self.session.flush()
        except IntegrityError:
            # Rede de segurança contra corrida entre a checagem em UserService
            # e este flush. Descobre qual dos dois campos colidiu.
            self.session.rollback()
            if self.get_by_username(user.username):
                raise username_already_exists(user.username)
            if self.get_by_email(user.email):
                raise email_already_exists(user.email)
            raise

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        model = self.session.get(UserModel, str(user_id))
        return self._to_domain(model) if model else None

    def get_by_email(self, email: str) -> Optional[User]:
        model = self.session.query(UserModel).filter(func.lower(UserModel.email) == email.lower()).first()
        return self._to_domain(model) if model else None

    def get_by_username(self, username: str) -> Optional[User]:
        model = self.session.query(UserModel).filter(func.lower(UserModel.username) == username.lower()).first()
        return self._to_domain(model) if model else None

    def exists_with_role(self, role: Role) -> bool:
        return self.session.query(UserModel.id).filter(UserModel.role == role).first() is not None

    def list_all(self) -> list[User]:
        return [self._to_domain(m) for m in self.session.query(UserModel).all()]

    def list_page(
        self, page: int, page_size: int, sort_by: str = "name", descending: bool = False,
        search: Optional[str] = None,
    ) -> Page[User]:
        if sort_by not in SORTABLE_FIELDS:
            raise ValueError(f"Campo de ordenação inválido: {sort_by!r}.")
        columns = {"name": UserModel.name, "username": UserModel.username, "email": UserModel.email}
        key = func.lower(columns[sort_by])
        query = self.session.query(UserModel)
        if search:
            query = query.filter(or_(*(_contains(columns[field], search) for field in SORTABLE_FIELDS)))
        # Empates (só possíveis no nome, que não é único) desempatam por nome de usuário e id.
        order = [key.desc() if descending else key.asc(), func.lower(UserModel.username), UserModel.id]
        total = query.with_entities(func.count(UserModel.id)).scalar()
        models = query.order_by(*order).offset((page - 1) * page_size).limit(page_size).all()
        return Page(items=[self._to_domain(m) for m in models], total=total)

    def delete(self, user_id: uuid.UUID) -> None:
        model = self.session.get(UserModel, str(user_id))
        if model:
            self.session.delete(model)
            self.session.flush()

    def has_dependencies(self, user_id: uuid.UUID) -> bool:
        return has_dependent_rows(self.session, UserModel.__tablename__, str(user_id))
