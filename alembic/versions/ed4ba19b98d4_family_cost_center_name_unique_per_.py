"""family_cost_center_name_unique_per_family_case_insensitive

Revision ID: ed4ba19b98d4
Revises: be0f02ce1b75
Create Date: 2026-09-29 20:21:30.553835

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed4ba19b98d4'
down_revision: Union[str, Sequence[str], None] = 'be0f02ce1b75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Índice funcional: autogenerate não reflete índices sobre expressão,
    # por isso escrito manualmente (mesma situação de ix_families_name_lower).
    op.create_index(
        "ix_family_cost_centers_family_id_name_lower",
        "family_cost_centers",
        ["family_id", sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_family_cost_centers_family_id_name_lower", table_name="family_cost_centers")
