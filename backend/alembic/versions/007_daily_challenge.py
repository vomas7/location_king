"""daily challenge: одна серия раундов на сутки для всех

Revision ID: 007
Revises: 006
Create Date: 2026-08-27 00:00:00.000000
"""

import geoalchemy2
import sqlalchemy as sa

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_challenges",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("day"),
    )

    op.create_table(
        "daily_rounds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "day",
            sa.Date(),
            sa.ForeignKey("daily_challenges.day", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("location_zones.id"), nullable=False),
        sa.Column(
            "target_point",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column("tile_zoom", sa.SmallInteger(), nullable=False),
        sa.Column("tile_x", sa.Integer(), nullable=False),
        sa.Column("tile_y", sa.Integer(), nullable=False),
        sa.Column("view_extent_km", sa.Numeric(8, 3), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("day", "position", name="uq_daily_rounds_day_position"),
    )
    op.create_index("ix_daily_rounds_day", "daily_rounds", ["day"])

    op.add_column("game_sessions", sa.Column("challenge_day", sa.Date(), nullable=True))
    op.create_index("ix_game_sessions_challenge_day", "game_sessions", ["challenge_day"])

    # Челлендж дня играется один раз: партий с одним и тем же днём у игрока
    # быть не должно. Обычные партии challenge_day не заполняют и под условие
    # не попадают.
    op.create_index(
        "uq_game_sessions_user_challenge",
        "game_sessions",
        ["user_id", "challenge_day"],
        unique=True,
        postgresql_where=sa.text("challenge_day IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_game_sessions_user_challenge", table_name="game_sessions")
    op.drop_index("ix_game_sessions_challenge_day", table_name="game_sessions")
    op.drop_column("game_sessions", "challenge_day")

    op.drop_index("ix_daily_rounds_day", table_name="daily_rounds")
    op.drop_table("daily_rounds")
    op.drop_table("daily_challenges")
