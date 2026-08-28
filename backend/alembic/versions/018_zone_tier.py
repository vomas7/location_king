"""Уровень зоны вместо уровня-категории.

Уровень партии выводился из категории: города — «средне», поля и острова —
«сложно», дикая природа — «хардкор». Из-за этого «средне» оказалось четырьмя
пятыми каталога и складывало Гамбург с Сурабаей: обе зоны — «city», а
угадываются совершенно по-разному.

Узнаваемость места из данных о местности не выводится, её может проставить
только человек, — поэтому теперь она хранится у зоны. Значение приезжает из
каталога следующим запуском scripts/seed.py; до него все зоны считаются
средним уровнем, чтобы игра не осталась без зон.

Revision ID: 018
Revises: 017
"""

import sqlalchemy as sa
from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "location_zones",
        sa.Column("tier", sa.String(length=20), nullable=False, server_default="normal"),
    )
    op.create_index("ix_location_zones_tier", "location_zones", ["tier"])

    # Дикая природа отделяется сразу: без этого до первого seed игрок с
    # хардкором получал бы города, а со средним — тайгу
    op.execute(
        """
        UPDATE location_zones
        SET tier = 'hardcore'
        WHERE category IN ('nature', 'mountains', 'desert', 'polar')
        """
    )
    op.execute(
        """
        UPDATE location_zones
        SET tier = 'hard'
        WHERE category IN ('rural', 'islands')
        """
    )


def downgrade() -> None:
    op.drop_index("ix_location_zones_tier", table_name="location_zones")
    op.drop_column("location_zones", "tier")
