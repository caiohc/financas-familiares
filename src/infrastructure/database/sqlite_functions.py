import sqlite3

from sqlalchemy import event
from sqlalchemy.engine import Engine

from domain.shared.text import fold_text


@event.listens_for(Engine, "connect")
def _register_sqlite_functions(dbapi_connection, connection_record) -> None:
    """
    O lower() do SQLite só trata ASCII ("É" não vira "é"). A pesquisa usa fold(), que
    ignora caixa e acentos, registrada em toda conexão SQLite. Não exige migration.
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.create_function("fold", 1, fold_text, deterministic=True)
