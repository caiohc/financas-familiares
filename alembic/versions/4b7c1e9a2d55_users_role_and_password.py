"""users_role_name_and_password

Revision ID: 4b7c1e9a2d55
Revises: 18ca5af21137
Create Date: 2026-10-31 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b7c1e9a2d55'
down_revision: Union[str, Sequence[str], None] = '18ca5af21137'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    As colunas são NOT NULL e sem valor padrão: a migração pressupõe a tabela
    `users` vazia (ela foi criada na revisão anterior, antes de existir cadastro).

    O batch do SQLite recria a tabela e não reflete índices sobre expressão, que
    seriam perdidos em silêncio: por isso os índices únicos de lower(username) e
    lower(email) são derrubados antes e recriados depois.
    """
    _drop_functional_indexes()
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'role',
            sa.Enum('ROOT', 'SYSTEM_ADMIN', 'FAMILY_ADMIN', 'FAMILY_USER', name='role'),
            nullable=False,
        ))
        batch_op.add_column(sa.Column('name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('password_hash', sa.String(length=255), nullable=False))
        batch_op.add_column(sa.Column('must_change_password', sa.Boolean(), nullable=False))
        batch_op.create_check_constraint('ck_users_role_family', "(role IN ('ROOT', 'SYSTEM_ADMIN') AND family_id IS NULL) OR (role NOT IN ('ROOT', 'SYSTEM_ADMIN') AND family_id IS NOT NULL)")
        batch_op.create_check_constraint('ck_users_name_required', "role = 'ROOT' OR (name IS NOT NULL AND trim(name) <> '')")
    _create_functional_indexes()


def downgrade() -> None:
    """Downgrade schema."""
    _drop_functional_indexes()
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('ck_users_name_required', type_='check')
        batch_op.drop_constraint('ck_users_role_family', type_='check')
        batch_op.drop_column('must_change_password')
        batch_op.drop_column('password_hash')
        batch_op.drop_column('name')
        batch_op.drop_column('role')
    _create_functional_indexes()


def _drop_functional_indexes() -> None:
    op.drop_index("ix_users_email_lower", table_name="users")
    op.drop_index("ix_users_username_lower", table_name="users")


def _create_functional_indexes() -> None:
    op.create_index("ix_users_username_lower", "users", [sa.text("lower(username)")], unique=True)
    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True)
