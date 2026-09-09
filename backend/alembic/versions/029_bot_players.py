"""Соперники-боты

Бот — это обычная учётная запись с поднятым флагом. Отдельной таблицей его
делать нельзя: он входит в комнату, играет серию и попадает в таблицу
результатов ровно тем же кодом, что и человек, — а на отдельный тип игрока
пришлось бы разветвить половину сервисов.

Флаг нужен, чтобы бота было видно снаружи и чтобы его не считали за человека:
по нему он исчезает из счётчика игроков, из таблицы лидеров и из поиска
друзей.

Revision ID: 029
Revises: 028
"""

import sqlalchemy as sa
from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Индекс частичный: ботов единицы, а исключать их приходится в каждом
    # запросе, который считает людей
    op.create_index(
        "ix_users_is_bot", "users", ["is_bot"], postgresql_where=sa.text("is_bot")
    )


def downgrade() -> None:
    op.drop_index("ix_users_is_bot", table_name="users")
    op.drop_column("users", "is_bot")
