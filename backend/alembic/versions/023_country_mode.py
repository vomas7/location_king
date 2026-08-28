"""Режим «угадай страну».

Тот же снимок и та же карта, но засчитывается попадание в страну, а не в
точку. Ставит игрок по-прежнему точку — в какую страну она попала, решает
сервер по границам.

Страна цели считается один раз, при сборке серии: у всех, кто играет одну
серию — челлендж дня, комнату, дуэль, — правильный ответ обязан быть один и
тот же. Пересчитывать его на каждую догадку значило бы зависеть от того, не
поменялись ли границы между двумя партиями.

Revision ID: 023
Revises: 022
"""

import sqlalchemy as sa
from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "round_series",
        sa.Column("answer_mode", sa.String(length=20), nullable=False, server_default="point"),
    )
    op.add_column("series_rounds", sa.Column("country_code", sa.String(length=3), nullable=True))

    op.add_column("rounds", sa.Column("country_code", sa.String(length=3), nullable=True))
    op.add_column("rounds", sa.Column("guess_country_code", sa.String(length=3), nullable=True))


def downgrade() -> None:
    op.drop_column("rounds", "guess_country_code")
    op.drop_column("rounds", "country_code")
    op.drop_column("series_rounds", "country_code")
    op.drop_column("round_series", "answer_mode")
