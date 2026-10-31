from application.interfaces.unit_of_work import AbstractUnitOfWork
from infrastructure.repositories.sqlalchemy.sqlalchemy_family_repository import SQLAlchemyFamilyRepository
from infrastructure.repositories.sqlalchemy.sqlalchemy_family_cost_center_repository import (
    SQLAlchemyFamilyCostCenterRepository,
)
from infrastructure.repositories.sqlalchemy.sqlalchemy_member_repository import SQLAlchemyMemberRepository
from infrastructure.repositories.sqlalchemy.sqlalchemy_category_repository import SQLAlchemyCategoryRepository
from infrastructure.repositories.sqlalchemy.sqlalchemy_user_repository import SQLAlchemyUserRepository

class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """
    Implementação concreta do UoW para SQLAlchemy.
    Gerencia a sessão e os repositórios reais da aplicação.
    """
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def __enter__(self):
        # Abre uma nova transação usando a fábrica (SessionLocal)
        self.session = self.session_factory()
        
        # Instancia e expõe os repositórios atrelados a esta sessão
        self.families = SQLAlchemyFamilyRepository(self.session)
        self.members = SQLAlchemyMemberRepository(self.session)
        self.categories = SQLAlchemyCategoryRepository(self.session)
        self.family_cost_centers = SQLAlchemyFamilyCostCenterRepository(self.session)
        self.users = SQLAlchemyUserRepository(self.session)

        return super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)
        # Como abolimos o scoped_session, a responsabilidade de devolver
        # a conexão para o pool do SQLAlchemy é puramente do UnitOfWork.
        self.session.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
