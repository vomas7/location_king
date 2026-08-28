"""Границы стран.

Нужны режиму «угадай страну»: игрок ставит точку так же, как обычно, а сервер
решает, в какую страну он попал. Считать это на клиенте значило бы отдать ему
границы целиком — два мегабайта, которые вдобавок подсказывают ответ.

Данные из OpenStreetMap (ODbL), загружаются scripts/load_countries.py. В
миграции только форма таблицы: границы — это данные, и место им рядом с
каталогом зон, а не в истории схемы.

Revision ID: 022
Revises: 021
"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("code", sa.String(length=3), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "border",
            geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326),
            nullable=False,
        ),
    )

    # Без индекса поиск страны по точке — это перебор двухсот тридцати шести
    # мультиполигонов на каждую догадку
    op.create_index(
        "ix_countries_border",
        "countries",
        ["border"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("ix_countries_border", table_name="countries")
    op.drop_table("countries")
