"""Подсказка в раунде.

Игрок может раскрыть, где искать, — часть света, страну или регион — ценой
части очков раунда. Отметка нужна, чтобы подсказку нельзя было взять дважды и
чтобы она не пропадала при перезагрузке страницы: сам текст не хранится, он
выводится из зоны и условий партии.

Revision ID: 017
Revises: 016
"""

import sqlalchemy as sa
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rounds",
        sa.Column("hint_used", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("rounds", "hint_used")
