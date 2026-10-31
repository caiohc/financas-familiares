from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from infrastructure.database.models import Base


def has_dependent_rows(session: Session, table_name: str, entity_id: str) -> bool:
    """
    Verifica se alguma linha, em qualquer tabela, referencia `entity_id` via FK.

    As referências vêm do próprio modelo (Base.metadata), não de uma lista
    mantida à mão: uma tabela nova com FK para `table_name` entra na checagem
    automaticamente. Tabelas mapeadas mas ainda não migradas no banco (fatias
    verticais futuras) são ignoradas: se a tabela não existe, não há linha
    dependente nela, e consultá-la daria erro.
    """
    existing_tables = set(inspect(session.connection()).get_table_names())

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        for fk in table.foreign_keys:
            if fk.column.table.name != table_name:
                continue
            query = select(fk.parent).where(fk.parent == entity_id).limit(1)
            if session.execute(query).first() is not None:
                return True

    return False
