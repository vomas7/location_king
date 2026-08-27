"""drop guests: играть можно только с учётной записью

Revision ID: 006
Revises: 005
Create Date: 2026-08-27 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Гостевые учётки одноразовые: пароля у них нет, войти под ними нельзя,
    # в таблицу лидеров они не попадали. Партии уезжают по каскаду.
    op.execute("DELETE FROM users WHERE is_guest = true")

    # То же для учёток, оставшихся от Keycloak: они помечались гостевыми
    # миграцией 004, но на всякий случай убираем и всё без пароля.
    op.execute("DELETE FROM users WHERE password_hash IS NULL OR email IS NULL")

    op.drop_column("users", "is_guest")

    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)


def downgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)

    op.add_column(
        "users",
        sa.Column("is_guest", sa.Boolean(), nullable=False, server_default="false"),
    )
