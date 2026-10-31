"""users table

Revision ID: 18ca5af21137
Revises: 9d4e2a7b1c30
Create Date: 2026-10-31 17:05:21.312507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18ca5af21137'
down_revision: Union[str, Sequence[str], None] = '9d4e2a7b1c30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('family_id', sa.String(length=36), nullable=True),
    sa.Column('username', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.ForeignKeyConstraint(['family_id'], ['families.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index('ix_users_family_id', ['family_id'], unique=False)

    # Índices funcionais: autogenerate não reflete índices sobre expressão,
    # por isso escritos manualmente. Unicidade global e case-insensitive.
    op.create_index("ix_users_username_lower", "users", [sa.text("lower(username)")], unique=True)
    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_users_email_lower", table_name="users")
    op.drop_index("ix_users_username_lower", table_name="users")
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_family_id')

    op.drop_table('users')
