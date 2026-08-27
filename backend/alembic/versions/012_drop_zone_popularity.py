"""drop zone popularity and is_featured: поля, которые никто не читал

Revision ID: 012
Revises: 011
Create Date: 2026-08-27 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # popularity увеличивался при создании раунда и больше нигде не появлялся.
    # Сколько раз в зоне играли, честно считает total_rounds — по самим
    # раундам, а не по счётчику, который к тому же не увеличивался в сериях.
    op.drop_column("location_zones", "popularity")

    # is_featured нигде не выставлялся в true и нигде не проверялся: витрины
    # избранных зон в игре нет, а индекс по нему база поддерживала честно.
    op.drop_index("ix_location_zones_is_featured", table_name="location_zones")
    op.drop_column("location_zones", "is_featured")


def downgrade() -> None:
    op.add_column(
        "location_zones",
        sa.Column("popularity", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "location_zones",
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_location_zones_is_featured", "location_zones", ["is_featured"])
