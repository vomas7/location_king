"""round timer: режимы с ограничением времени на раунд

Revision ID: 009
Revises: 008
Create Date: 2026-08-27 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NULL — играем без ограничения времени
    op.add_column(
        "game_sessions",
        sa.Column("time_limit_seconds", sa.SmallInteger(), nullable=True),
    )

    # Срок ставит сервер при создании раунда: часы игрока к делу не относятся
    op.add_column("rounds", sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rounds", sa.Column("answer_seconds", sa.Numeric(6, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("rounds", "answer_seconds")
    op.drop_column("rounds", "deadline_at")
    op.drop_column("game_sessions", "time_limit_seconds")
