"""neutral display names: имя в таблице лидеров не должно быть частью почты

Revision ID: 013
Revises: 012
Create Date: 2026-08-27 00:00:00.000000
"""

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # При регистрации в display_name подставлялась часть адреса до собаки, и
    # почта игрока оказывалась в публичной таблице лидеров. Такие имена
    # заменяем нейтральными; те, что игрок задал сам, не трогаем.
    op.execute(
        """
        UPDATE users
        SET display_name = 'Игрок ' || upper(substr(md5(random()::text || id::text), 1, 4))
        WHERE display_name IS NULL
           OR display_name = split_part(email, '@', 1)
        """
    )


def downgrade() -> None:
    # Прежние значения восстановить неоткуда, да и возвращать почту в
    # публичную таблицу незачем.
    pass
