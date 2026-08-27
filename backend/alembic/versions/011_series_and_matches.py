"""series and matches: одна реализация серии раундов и комнаты мультиплеера

Revision ID: 011
Revises: 010
Create Date: 2026-08-27 00:00:00.000000
"""

import geoalchemy2
import sqlalchemy as sa

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Серия раундов: общая для челленджа дня и комнаты ─────────────────
    op.create_table(
        "round_series",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "series_rounds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "series_id",
            sa.Integer(),
            sa.ForeignKey("round_series.id", ondelete="CASCADE"),
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
        sa.UniqueConstraint("series_id", "position", name="uq_series_rounds_position"),
    )
    op.create_index("ix_series_rounds_series_id", "series_rounds", ["series_id"])

    # ── Челлендж переезжает на общую серию ───────────────────────────────
    op.add_column("daily_challenges", sa.Column("series_id", sa.Integer(), nullable=True))

    # Для каждого существующего дня заводим серию и переносим в неё раунды
    op.execute(
        """
        WITH created AS (
            INSERT INTO round_series (created_at)
            SELECT created_at FROM daily_challenges ORDER BY day
            RETURNING id
        ), numbered AS (
            SELECT id, row_number() OVER (ORDER BY id) AS n FROM created
        ), days AS (
            SELECT day, row_number() OVER (ORDER BY day) AS n FROM daily_challenges
        )
        UPDATE daily_challenges
        SET series_id = numbered.id
        FROM numbered, days
        WHERE days.n = numbered.n AND daily_challenges.day = days.day
        """
    )
    op.execute(
        """
        INSERT INTO series_rounds
            (series_id, position, zone_id, target_point, tile_zoom, tile_x, tile_y, view_extent_km)
        SELECT c.series_id, r.position, r.zone_id, r.target_point,
               r.tile_zoom, r.tile_x, r.tile_y, r.view_extent_km
        FROM daily_rounds r
        JOIN daily_challenges c ON c.day = r.day
        """
    )

    # Дни без раундов оставаться не должны: без серии челлендж бессмыслен
    op.execute("DELETE FROM daily_challenges WHERE series_id IS NULL")
    op.alter_column("daily_challenges", "series_id", nullable=False)
    op.create_foreign_key(
        "fk_daily_challenges_series",
        "daily_challenges",
        "round_series",
        ["series_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index("ix_daily_rounds_day", table_name="daily_rounds")
    op.drop_table("daily_rounds")

    # ── Комнаты мультиплеера ─────────────────────────────────────────────
    op.create_table(
        "matches",
        sa.Column("code", sa.String(8), nullable=False),
        sa.Column(
            "host_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "series_id",
            sa.Integer(),
            sa.ForeignKey("round_series.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rounds_total", sa.SmallInteger(), nullable=False),
        sa.Column("time_limit_seconds", sa.SmallInteger(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_index("ix_matches_host_user_id", "matches", ["host_user_id"])

    # ── Партия знает свою серию и комнату ────────────────────────────────
    op.add_column("game_sessions", sa.Column("series_id", sa.Integer(), nullable=True))
    op.add_column("game_sessions", sa.Column("match_code", sa.String(8), nullable=True))
    op.create_foreign_key(
        "fk_game_sessions_series",
        "game_sessions",
        "round_series",
        ["series_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_game_sessions_match",
        "game_sessions",
        "matches",
        ["match_code"],
        ["code"],
        ondelete="SET NULL",
    )
    op.create_index("ix_game_sessions_match_code", "game_sessions", ["match_code"])

    # Сыгранным челленджам проставляем серию их дня
    op.execute(
        """
        UPDATE game_sessions SET series_id = c.series_id
        FROM daily_challenges c
        WHERE game_sessions.challenge_day = c.day
        """
    )

    # В одной комнате игрок играет один раз
    op.create_index(
        "uq_game_sessions_user_match",
        "game_sessions",
        ["user_id", "match_code"],
        unique=True,
        postgresql_where=sa.text("match_code IS NOT NULL"),
    )

    # Колонка mode никогда не читалась: режим партии однозначно виден по
    # challenge_day и match_code, второе место для той же истины не нужно
    op.drop_column("game_sessions", "mode")


def downgrade() -> None:
    op.add_column(
        "game_sessions",
        sa.Column("mode", sa.String(20), nullable=False, server_default="solo"),
    )

    op.drop_index("uq_game_sessions_user_match", table_name="game_sessions")
    op.drop_index("ix_game_sessions_match_code", table_name="game_sessions")
    op.drop_constraint("fk_game_sessions_match", "game_sessions", type_="foreignkey")
    op.drop_constraint("fk_game_sessions_series", "game_sessions", type_="foreignkey")
    op.drop_column("game_sessions", "match_code")
    op.drop_column("game_sessions", "series_id")

    op.drop_index("ix_matches_host_user_id", table_name="matches")
    op.drop_table("matches")

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

    op.execute(
        """
        INSERT INTO daily_rounds
            (day, position, zone_id, target_point, tile_zoom, tile_x, tile_y, view_extent_km)
        SELECT c.day, r.position, r.zone_id, r.target_point,
               r.tile_zoom, r.tile_x, r.tile_y, r.view_extent_km
        FROM series_rounds r
        JOIN daily_challenges c ON c.series_id = r.series_id
        """
    )

    op.drop_constraint("fk_daily_challenges_series", "daily_challenges", type_="foreignkey")
    op.drop_column("daily_challenges", "series_id")

    op.drop_index("ix_series_rounds_series_id", table_name="series_rounds")
    op.drop_table("series_rounds")
    op.drop_table("round_series")
