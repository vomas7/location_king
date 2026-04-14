"""initial: postgis + all tables

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── PostGIS расширение ────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")

    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keycloak_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("total_score", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_keycloak_id", "users", ["keycloak_id"], unique=True)

    # ── location_zones ────────────────────────────────────────────────────
    op.create_table(
        "location_zones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column(
            "polygon",
            geoalchemy2.types.Geometry(geometry_type="POLYGON", srid=4326),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_difficulty_range"),
    )
    op.create_index("ix_location_zones_category", "location_zones", ["category"])
    op.create_index("ix_location_zones_is_active", "location_zones", ["is_active"])
    # Пространственный индекс для ST_Contains и ST_Within запросов
    op.create_index(
        "ix_location_zones_polygon",
        "location_zones",
        ["polygon"],
        postgresql_using="gist",
    )

    # ── game_sessions ─────────────────────────────────────────────────────
    op.create_table(
        "game_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode", sa.String(20), nullable=False, server_default="solo"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("rounds_total", sa.SmallInteger(), nullable=False, server_default="5"),
        sa.Column("rounds_done", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_game_sessions_user_id", "game_sessions", ["user_id"])
    op.create_index("ix_game_sessions_status", "game_sessions", ["status"])

    # ── rounds ────────────────────────────────────────────────────────────
    op.create_table(
        "rounds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("game_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "zone_id",
            sa.Integer(),
            sa.ForeignKey("location_zones.id"),
            nullable=False,
        ),
        sa.Column(
            "target_point",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column(
            "guess_point",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("distance_km", sa.Numeric(10, 2), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("view_extent_km", sa.SmallInteger(), nullable=False, server_default="500"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("guessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rounds_session_id", "rounds", ["session_id"])


def downgrade() -> None:
    op.drop_table("rounds")
    op.drop_table("game_sessions")
    op.drop_table("location_zones")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS postgis_topology")
    op.execute("DROP EXTENSION IF EXISTS postgis CASCADE")
