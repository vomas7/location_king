"""Закрыть партии, начатые до перехода на серии раундов.

У таких партий не сохранены условия набора, и следующий раунд собрать не из
чего. Оставленные активными, они отвечали бы ошибкой на каждую догадку и
предлагались бы игроку кнопкой «продолжить».

Revision ID: 014
Revises: 013
"""

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE game_sessions
        SET status = 'abandoned',
            finished_at = COALESCE(finished_at, NOW())
        WHERE status = 'active' AND series_id IS NULL
        """
    )


def downgrade() -> None:
    # Обратно не восстановить: какие партии были активны, нигде не записано
    pass
