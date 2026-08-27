"""round tiles: показываемая область как тайл Web Mercator

Revision ID: 005
Revises: 004
Create Date: 2026-08-26 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

# Поля, оставшиеся от режима, где клиент получал готовый URL снимка
UNUSED_ROUND_COLUMNS = [
    ("satellite_image_url", sa.Text(), None),
    ("hint_used", sa.Boolean(), "false"),
    ("notes", sa.Text(), None),
    ("time_limit_seconds", sa.SmallInteger(), None),
    ("started_at", sa.DateTime(timezone=True), None),
    ("completed_at", sa.DateTime(timezone=True), None),
]

UNUSED_SESSION_COLUMNS = [
    ("time_control", sa.String(20), "'unlimited'"),
    ("best_round_score", sa.Integer(), "0"),
    ("worst_round_score", sa.Integer(), "0"),
    ("title", sa.String(100), None),
    ("description", sa.Text(), None),
    ("is_public", sa.Boolean(), "false"),
    ("allow_comments", sa.Boolean(), "true"),
    ("last_activity_at", sa.DateTime(timezone=True), None),
]


def upgrade() -> None:
    # ── тайл, который показывается игроку ─────────────────────────────────
    # Незавершённые раунды старого формата продолжить нельзя: у них нет тайла.
    op.execute("DELETE FROM rounds WHERE guess_point IS NULL")

    op.add_column("rounds", sa.Column("tile_zoom", sa.SmallInteger(), nullable=True))
    op.add_column("rounds", sa.Column("tile_x", sa.Integer(), nullable=True))
    op.add_column("rounds", sa.Column("tile_y", sa.Integer(), nullable=True))

    # Для сыгранных раундов тайл восстанавливаем из координат цели: зум 13 —
    # ближайший к прежней области в несколько километров.
    op.execute(
        """
        UPDATE rounds SET
            tile_zoom = 13,
            tile_x = floor((ST_X(target_point) + 180.0) / 360.0 * 8192)::int,
            tile_y = floor(
                (1.0 - asinh(tan(radians(ST_Y(target_point)))) / pi()) / 2.0 * 8192
            )::int
        WHERE tile_zoom IS NULL
        """
    )

    for column in ("tile_zoom", "tile_x", "tile_y"):
        op.alter_column("rounds", column, nullable=False)

    # ── размер области стал дробным: тайл редко бывает ровно в километрах ──
    op.alter_column(
        "rounds",
        "view_extent_km",
        type_=sa.Numeric(8, 3),
        existing_type=sa.SmallInteger(),
        server_default=None,
        postgresql_using="view_extent_km::numeric(8,3)",
    )
    op.alter_column("rounds", "distance_km", type_=sa.Numeric(10, 3), existing_type=sa.Numeric(10, 2))

    # Раунд создаётся сразу активным: состояния «ожидает начала» больше нет
    op.execute("UPDATE rounds SET status = 'active' WHERE status = 'pending'")
    op.alter_column("rounds", "status", server_default="active")

    for name, _type, _default in UNUSED_ROUND_COLUMNS:
        op.drop_column("rounds", name)
    for name, _type, _default in UNUSED_SESSION_COLUMNS:
        op.drop_column("game_sessions", name)

    op.alter_column("game_sessions", "average_score", type_=sa.Float(), existing_type=sa.Integer())


def downgrade() -> None:
    op.alter_column("rounds", "status", server_default="pending")
    op.alter_column("game_sessions", "average_score", type_=sa.Integer(), existing_type=sa.Float())

    for name, type_, default in reversed(UNUSED_SESSION_COLUMNS):
        op.add_column(
            "game_sessions",
            sa.Column(name, type_, nullable=True, server_default=default),
        )

    # Индекс уехал вместе со своей колонкой — возвращаем, иначе downgrade 002 падает
    op.create_index("ix_game_sessions_is_public", "game_sessions", ["is_public"])
    for name, type_, default in reversed(UNUSED_ROUND_COLUMNS):
        op.add_column("rounds", sa.Column(name, type_, nullable=True, server_default=default))

    op.alter_column("rounds", "distance_km", type_=sa.Numeric(10, 2), existing_type=sa.Numeric(10, 3))
    op.alter_column(
        "rounds",
        "view_extent_km",
        type_=sa.SmallInteger(),
        existing_type=sa.Numeric(8, 3),
        server_default="500",
        postgresql_using="view_extent_km::smallint",
    )

    op.drop_column("rounds", "tile_y")
    op.drop_column("rounds", "tile_x")
    op.drop_column("rounds", "tile_zoom")
