"""Варианты ответа для режима выбора

Revision ID: 027
Revises: 026
"""

import sqlalchemy as sa
from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("series_rounds", sa.Column("choices", sa.String(length=80), nullable=True))
    op.add_column("rounds", sa.Column("choices", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("rounds", "choices")
    op.drop_column("series_rounds", "choices")
