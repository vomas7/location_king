"""Свой кадр у зоны

Достопримечательности показываются крупным планом: Колизей в кадре на сорок
пять километров — это Рим, а не Колизей. Кадр остальных зон по-прежнему
выводится из уровня, поэтому колонка пустая почти у всех.

Revision ID: 028
Revises: 027
"""

import sqlalchemy as sa
from alembic import op

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("location_zones", sa.Column("view_extent_km", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("location_zones", "view_extent_km")
