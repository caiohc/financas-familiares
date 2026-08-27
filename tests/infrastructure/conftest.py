import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from infrastructure.database.models import Base

@pytest.fixture(scope="session")
def engine():
    engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def session(engine) -> Session:
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
