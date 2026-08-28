"""Убрать цифру сложности у зоны.

Сложность партии теперь выбирается уровнем — легко, средне, сложно, хардкор, —
а какие зоны попадают на уровень, определяет их категория. Отдельное число от
одного до пяти при этом никем не читается.

Revision ID: 015
Revises: 014
"""

import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_location_zones_difficulty", table_name="location_zones")
    op.drop_column("location_zones", "difficulty")


def downgrade() -> None:
    op.add_column(
        "location_zones",
        sa.Column("difficulty", sa.SmallInteger(), nullable=False, server_default="1"),
    )
    op.create_index("ix_location_zones_difficulty", "location_zones", ["difficulty"])

    # Ограничение уходит вместе со столбцом, а откат ревизии 003 рассчитывает
    # его застать. Без этой строки цепочка вниз обрывается на ровном месте
    op.create_check_constraint(
        "ck_difficulty_range", "location_zones", sa.text("difficulty BETWEEN 1 AND 7")
    )
