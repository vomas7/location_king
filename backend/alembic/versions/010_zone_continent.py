"""zone continent: фильтр игровых зон по частям света

Revision ID: 010
Revises: 009
Create Date: 2026-08-27 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("location_zones", sa.Column("continent", sa.String(20), nullable=True))
    op.create_index("ix_location_zones_continent", "location_zones", ["continent"])


def downgrade() -> None:
    op.drop_index("ix_location_zones_continent", table_name="location_zones")
    op.drop_column("location_zones", "continent")
