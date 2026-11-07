"""accounts_and_invitations

Revision ID: 7c3f9d1a8b42
Revises: 4b7c1e9a2d55
Create Date: 2026-11-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c3f9d1a8b42'
down_revision: Union[str, Sequence[str], None] = '4b7c1e9a2d55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CK_PASSWORD_REQUIRES_ACTIVATION = "password_hash IS NULL OR activated_at IS NOT NULL"
CK_ROOT_HAS_PASSWORD = "role <> 'ROOT' OR password_hash IS NOT NULL"


def upgrade() -> None:
    """Upgrade schema.

    O administrador deixa de definir senhas: o usuário nasce sem senha (conta pendente) e a define
    por um convite (link por e-mail + código por outro canal). Por isso `password_hash` passa a
    aceitar nulo, `must_change_password` deixa de existir e entram `is_active` e `activated_at`.

    Contas que já têm senha (ex.: o root criado pela CLI) passam a contar como ativadas agora.

    O batch do SQLite recria a tabela e não reflete índices sobre expressão, que seriam perdidos
    em silêncio: os índices únicos de lower(username) e lower(email) são derrubados antes e
    recriados depois.
    """
    _drop_functional_indexes()

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        batch_op.add_column(sa.Column('activated_at', sa.DateTime(), nullable=True))

    op.execute("UPDATE users SET activated_at = CURRENT_TIMESTAMP WHERE password_hash IS NOT NULL")

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash', existing_type=sa.String(length=255), nullable=True)
        batch_op.drop_column('must_change_password')
        batch_op.create_check_constraint('ck_users_password_requires_activation', CK_PASSWORD_REQUIRES_ACTIVATION)
        batch_op.create_check_constraint('ck_users_root_has_password', CK_ROOT_HAS_PASSWORD)

    _create_functional_indexes()

    op.create_table(
        'user_invitations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('purpose', sa.Enum('ACTIVATION', 'ADMIN_RESET', 'RECOVERY', name='invitationpurpose'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('code_hash', sa.String(length=255), nullable=True),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('consumed_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "(purpose = 'RECOVERY' AND code_hash IS NULL) OR (purpose <> 'RECOVERY' AND code_hash IS NOT NULL)",
            name='ck_user_invitations_code_by_purpose',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ux_user_invitations_token_hash', 'user_invitations', ['token_hash'], unique=True)
    op.create_index(
        'ux_user_invitations_one_active_per_user', 'user_invitations', ['user_id'], unique=True,
        sqlite_where=sa.text('consumed_at IS NULL AND revoked_at IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema.

    Falha se existir usuário sem senha (conta pendente ou aguardando nova senha): defina a senha
    dessas contas, ou exclua-as, antes de reverter. Os convites são descartados.
    """
    op.drop_index('ux_user_invitations_one_active_per_user', table_name='user_invitations')
    op.drop_index('ux_user_invitations_token_hash', table_name='user_invitations')
    op.drop_table('user_invitations')

    _drop_functional_indexes()

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('ck_users_root_has_password', type_='check')
        batch_op.drop_constraint('ck_users_password_requires_activation', type_='check')
        batch_op.add_column(sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.alter_column('password_hash', existing_type=sa.String(length=255), nullable=False)
        batch_op.drop_column('activated_at')
        batch_op.drop_column('is_active')

    _create_functional_indexes()


def _drop_functional_indexes() -> None:
    op.drop_index("ix_users_email_lower", table_name="users")
    op.drop_index("ix_users_username_lower", table_name="users")


def _create_functional_indexes() -> None:
    op.create_index("ix_users_username_lower", "users", [sa.text("lower(username)")], unique=True)
    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True)
