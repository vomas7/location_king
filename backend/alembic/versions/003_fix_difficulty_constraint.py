"""fix_difficulty_constraint: Update difficulty constraint from 1-5 to 1-7

Revision ID: 003
Revises: 002
Create Date: 2025-01-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Удаляем старый constraint
    op.drop_constraint("ck_difficulty_range", "location_zones", type_="check")
    
    # Создаём новый constraint с диапазоном 1-7
    op.create_check_constraint(
        "ck_difficulty_range",
        "location_zones",
        sa.text("difficulty BETWEEN 1 AND 7")
    )
    
    # Также обновляем view_extent_km в rounds с 500 до 50 (была опечатка в initial миграции)
    op.execute("""
        ALTER TABLE rounds 
        ALTER COLUMN view_extent_km 
        SET DEFAULT 5
    """)
    
    # Обновляем существующие записи если view_extent_km = 500 (ошибка в initial)
    op.execute("""
        UPDATE rounds 
        SET view_extent_km = 5 
        WHERE view_extent_km = 500
    """)


def downgrade() -> None:
    # Возвращаем старый constraint
    op.drop_constraint("ck_difficulty_range", "location_zones", type_="check")
    op.create_check_constraint(
        "ck_difficulty_range",
        "location_zones",
        sa.text("difficulty BETWEEN 1 AND 5")
    )
    
    # Возвращаем view_extent_km
    op.execute("""
        ALTER TABLE rounds 
        ALTER COLUMN view_extent_km 
        SET DEFAULT 500
    """)