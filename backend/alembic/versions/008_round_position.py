"""round position: номер раунда внутри партии хранится, а не вычисляется

Revision ID: 008
Revises: 007
Create Date: 2026-08-27 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rounds", sa.Column("position", sa.SmallInteger(), nullable=True))

    # Раунды создавались по порядку, поэтому номер восстанавливается по id
    op.execute(
        """
        UPDATE rounds SET position = numbered.position
        FROM (
            SELECT id, row_number() OVER (PARTITION BY session_id ORDER BY id) AS position
            FROM rounds
        ) AS numbered
        WHERE rounds.id = numbered.id
        """
    )

    op.alter_column("rounds", "position", nullable=False)
    op.create_unique_constraint("uq_rounds_session_position", "rounds", ["session_id", "position"])


def downgrade() -> None:
    op.drop_constraint("uq_rounds_session_position", "rounds", type_="unique")
    op.drop_column("rounds", "position")
