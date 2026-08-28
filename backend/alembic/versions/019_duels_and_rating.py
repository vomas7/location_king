"""Дуэли и рейтинг Эло.

Подбор соперника ставит в пару двоих с близким рейтингом и собирает им общую
серию раундов. Рейтинг считается только по таким дуэлям: там оба играют одно
и то же, и условия партии сокращаются. По обычным партиям сравнивать нельзя —
они у всех разной сложности, и средний промах на лёгком уровне по Европе в
десятки раз меньше, чем на хардкоре по всему миру.

Комнате нужен вид: дуэль от обычной комнаты отличается тем, что её собрал
сервер, формат у неё фиксированный и по её итогу меняется рейтинг. Отметка
rated_at не даёт начислить его дважды.

Revision ID: 019
Revises: 018
"""

import sqlalchemy as sa
from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None

# Совпадает с START_RATING в app/utils/elo.py. Здесь числом, а не импортом:
# миграция описывает состояние базы на своё время и не должна меняться следом
# за кодом
START_RATING = "1000"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("rating", sa.Integer(), nullable=False, server_default=START_RATING),
    )
    op.add_column(
        "users",
        sa.Column("duels_played", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_users_rating", "users", ["rating"])

    op.add_column(
        "matches",
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="room"),
    )
    op.add_column("matches", sa.Column("rated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_matches_kind", "matches", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_matches_kind", table_name="matches")
    op.drop_column("matches", "rated_at")
    op.drop_column("matches", "kind")

    op.drop_index("ix_users_rating", table_name="users")
    op.drop_column("users", "duels_played")
    op.drop_column("users", "rating")
