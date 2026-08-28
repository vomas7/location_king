"""Друзья.

Игроки добавляют друг друга по короткому коду, а не по имени: имена не
уникальны, и поиск по чужому имени — способ найти не того человека. Код
раздаётся всем существующим игрокам здесь же.

Дружба хранится одной строкой на пару, а не двумя встречными: две строки
пришлось бы держать согласованными, а «дружба есть у одного и нет у другого» —
состояние, которого быть не должно.

Revision ID: 021
Revises: 020
"""

import secrets

import sqlalchemy as sa
from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None

# Совпадает с app/utils/codes.py. Здесь своей копией: миграция описывает базу
# на своё время и не должна меняться следом за кодом
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
LENGTH = 6


def _code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def upgrade() -> None:
    op.add_column("users", sa.Column("friend_code", sa.String(length=8), nullable=True))

    # Каждому существующему игроку — свой код. По одному запросу на игрока:
    # их немного, а сгенерировать уникальные значения одним UPDATE нельзя
    users = sa.table("users", sa.column("id", sa.Integer), sa.column("friend_code", sa.String))
    connection = op.get_bind()

    taken: set[str] = set()
    for (user_id,) in connection.execute(sa.select(users.c.id)):
        code = _code()
        while code in taken:
            code = _code()
        taken.add(code)

        connection.execute(users.update().where(users.c.id == user_id).values(friend_code=code))

    op.alter_column("users", "friend_code", nullable=False)
    op.create_index("ix_users_friend_code", "users", ["friend_code"], unique=True)

    op.create_table(
        "friendships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "requester_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "addressee_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
    )
    op.create_index("ix_friendships_requester_id", "friendships", ["requester_id"])
    op.create_index("ix_friendships_addressee_id", "friendships", ["addressee_id"])
    op.create_index("ix_friendships_status", "friendships", ["status"])


def downgrade() -> None:
    op.drop_table("friendships")

    op.drop_index("ix_users_friend_code", table_name="users")
    op.drop_column("users", "friend_code")
