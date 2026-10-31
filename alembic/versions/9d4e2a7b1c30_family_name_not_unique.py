"""family_name_not_unique

Revision ID: 9d4e2a7b1c30
Revises: 325cae4b91da
Create Date: 2026-10-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d4e2a7b1c30'
down_revision: Union[str, Sequence[str], None] = '325cae4b91da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Várias famílias podem ter o mesmo nome (a identidade é o UUID). O índice
    # sobre lower(name) continua, agora não único, só para busca e ordenação.
    # Escrito à mão: autogenerate não reflete índices sobre expressão.
    op.drop_index("ix_families_name_lower", table_name="families")
    op.create_index("ix_families_name_lower", "families", [sa.text("lower(name)")])


def downgrade() -> None:
    """Downgrade schema.

    Falha se já existirem duas famílias com o mesmo nome (sem diferença de
    maiúsculas): nesse caso, renomeie-as antes de reverter.
    """
    op.drop_index("ix_families_name_lower", table_name="families")
    op.create_index("ix_families_name_lower", "families", [sa.text("lower(name)")], unique=True)
