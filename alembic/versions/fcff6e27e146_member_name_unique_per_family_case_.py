"""member_name_unique_per_family_case_insensitive

Revision ID: fcff6e27e146
Revises: ed4ba19b98d4
Create Date: 2026-10-28 21:18:40.256971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fcff6e27e146'
down_revision: Union[str, Sequence[str], None] = 'ed4ba19b98d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Índice funcional: autogenerate não reflete índices sobre expressão,
    # por isso escrito manualmente (mesma situação de ix_families_name_lower).
    op.create_index(
        "ix_members_family_id_name_lower",
        "members",
        ["family_id", sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_members_family_id_name_lower", table_name="members")
