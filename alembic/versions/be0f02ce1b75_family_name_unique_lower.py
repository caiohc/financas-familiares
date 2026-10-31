"""family_name_unique_lower

Revision ID: be0f02ce1b75
Revises: 21b23ea0d3f5
Create Date: 2026-09-23 19:53:25.231793

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be0f02ce1b75'
down_revision: Union[str, Sequence[str], None] = '21b23ea0d3f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Índice funcional: autogenerate não reflete índices sobre expressão,
    # por isso escrito manualmente.
    op.create_index(
        "ix_families_name_lower",
        "families",
        [sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_families_name_lower", table_name="families")
