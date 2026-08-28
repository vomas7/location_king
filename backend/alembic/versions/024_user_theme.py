"""Оформление интерфейса у игрока.

Тема хранится у игрока, а не в браузере: выбор должен пережить и очистку
хранилища, и переход на другое устройство — игра-то одна и та же.

Существующим игрокам достаётся тёмная: она у них и была, и менять её за них
было бы сюрпризом. Светлую и «как в системе» они выбирают сами.

Revision ID: 024
Revises: 023
"""

import sqlalchemy as sa
from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("theme", sa.String(length=10), nullable=False, server_default="dark"),
    )


def downgrade() -> None:
    op.drop_column("users", "theme")
