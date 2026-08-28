"""Запомнить, с какими условиями играли партию.

Таблица лидеров должна делиться по настройкам — по уровню и по месту, — а
партия до сих пор не помнила, с чем её начинали. Условия набора хранятся в
серии раундов: именно она из них и собрана.

Средний промах за партию считается заодно: без него зачёт по точности пришлось
бы каждый раз собирать по всем раундам всех игроков.

Revision ID: 016
Revises: 015
"""

import sqlalchemy as sa
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("round_series", sa.Column("difficulty", sa.String(length=20), nullable=True))
    op.add_column("round_series", sa.Column("continent", sa.String(length=20), nullable=True))
    op.add_column("round_series", sa.Column("country_group", sa.String(length=20), nullable=True))

    op.add_column("game_sessions", sa.Column("average_distance", sa.Float(), nullable=True))

    # Считаем средний промах для уже сыгранных партий: иначе зачёт по точности
    # начнётся с пустого места и старые результаты из него пропадут
    op.execute(
        """
        UPDATE game_sessions AS s
        SET average_distance = stats.value
        FROM (
            SELECT session_id, AVG(distance_km) AS value
            FROM rounds
            WHERE status = 'guessed' AND distance_km IS NOT NULL
            GROUP BY session_id
        ) AS stats
        WHERE stats.session_id = s.id
        """
    )


def downgrade() -> None:
    op.drop_column("game_sessions", "average_distance")
    op.drop_column("round_series", "country_group")
    op.drop_column("round_series", "continent")
    op.drop_column("round_series", "difficulty")
