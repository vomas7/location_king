"""own auth: password_hash, guests, no keycloak

Revision ID: 004
Revises: 003
Create Date: 2026-08-26 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

# Поля профиля, которых нет в игре: рейтинги, уровни, премиум-статус
UNUSED_USER_COLUMNS = [
    ("elo_rating", sa.Integer(), "1000"),
    ("rank", sa.String(50), None),
    ("level", sa.Integer(), "1"),
    ("experience", sa.Integer(), "0"),
    ("is_premium", sa.Boolean(), "false"),
    ("is_verified", sa.Boolean(), "false"),
    ("email_verified", sa.Boolean(), "false"),
    ("avatar_url", sa.Text(), None),
    ("bio", sa.Text(), None),
    ("country", sa.String(100), None),
    ("timezone", sa.String(50), None),
    ("language", sa.String(10), "'ru'"),
    ("games_won", sa.Integer(), "0"),
    ("worst_score", sa.Integer(), "0"),
    ("last_activity_at", sa.DateTime(timezone=True), None),
]


def upgrade() -> None:
    # ── собственная аутентификация вместо Keycloak ────────────────────────
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_guest", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Учётки, заведённые под Keycloak, паролей не имеют и войти по ним нельзя.
    # Помечаем их гостевыми, чтобы не выглядели полноценными аккаунтами.
    op.execute("UPDATE users SET is_guest = true WHERE keycloak_id IS NOT NULL")

    op.drop_index("ix_users_keycloak_id", table_name="users")
    op.drop_column("users", "keycloak_id")

    # email уникален и уже проиндексирован миграцией 002 — переиздаём индекс
    # только чтобы гарантировать уникальность после чистки данных
    op.execute("UPDATE users SET email = NULL WHERE email = ''")

    for name, _type, _default in UNUSED_USER_COLUMNS:
        op.drop_column("users", name)


def downgrade() -> None:
    for name, type_, default in reversed(UNUSED_USER_COLUMNS):
        op.add_column("users", sa.Column(name, type_, nullable=True, server_default=default))

    op.add_column("users", sa.Column("keycloak_id", postgresql.UUID(), nullable=True))
    op.create_index("ix_users_keycloak_id", "users", ["keycloak_id"], unique=True)

    op.drop_column("users", "is_guest")
    op.drop_column("users", "password_hash")
