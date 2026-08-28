"""Аватарка игрока.

Не файл, а два числа — форма узора и цвет: узор по ним рисует клиент. Отказ
от загрузки картинок осознанный, а не временный. Аватарку видно в таблице
лидеров и в комнате, то есть это публикация, и загруженные картинки
потребовали бы хранилища, обработки и, главное, модерации — за содержимое
отвечал бы владелец игры.

Значение по умолчанию у всех нулевое, но существующим игрокам оно
раздаётся здесь же по идентификатору: одинаковая заглушка у всех означала бы,
что аватарки нет.

Revision ID: 020
Revises: 019
"""

import sqlalchemy as sa
from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None

# Совпадает с SHAPES и COLORS в app/utils/avatar.py. Числами, а не импортом:
# миграция описывает базу на своё время и не должна меняться следом за кодом
SHAPES = 6
COLORS = 6


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("avatar_shape", sa.SmallInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("avatar_color", sa.SmallInteger(), nullable=False, server_default="0"),
    )

    op.execute(
        f"""
        UPDATE users
        SET avatar_shape = id % {SHAPES},
            avatar_color = (id / {SHAPES}) % {COLORS}
        """
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_color")
    op.drop_column("users", "avatar_shape")
