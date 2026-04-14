"""
Enum'ы для игровых моделей.
"""
from enum import StrEnum


class GameMode(StrEnum):
    """Режимы игры"""
    SOLO = "solo"
    MULTIPLAYER = "multiplayer"
    CHALLENGE = "challenge"  # Специальные челленджи
    PRACTICE = "practice"    # Тренировочный режим


class SessionStatus(StrEnum):
    """Статусы игровой сессии"""
    ACTIVE = "active"        # Активная сессия
    FINISHED = "finished"    # Завершённая сессия
    ABANDONED = "abandoned"  # Брошенная сессия
    PAUSED = "paused"        # Приостановленная сессия


class RoundStatus(StrEnum):
    """Статусы раунда"""
    PENDING = "pending"      # Ожидает начала
    ACTIVE = "active"        # Активный раунд
    GUESSED = "guessed"      # Догадка отправлена
    SKIPPED = "skipped"      # Пропущенный раунд
    TIMED_OUT = "timed_out"  # Время вышло


class DifficultyLevel(StrEnum):
    """Уровни сложности"""
    VERY_EASY = "very_easy"    # 1
    EASY = "easy"              # 2
    MEDIUM = "medium"          # 3
    HARD = "hard"              # 4
    VERY_HARD = "very_hard"    # 5
    EXPERT = "expert"          # 6
    MASTER = "master"          # 7


class ZoneCategory(StrEnum):
    """Категории игровых зон"""
    CITY = "city"               # Города
    NATURE = "nature"           # Природа
    COAST = "coast"             # Побережья
    MOUNTAINS = "mountains"     # Горы
    DESERT = "desert"           # Пустыни
    ISLANDS = "islands"         # Острова
    HISTORICAL = "historical"   # Исторические места
    ARCHITECTURE = "architecture" # Архитектура
    INDUSTRIAL = "industrial"   # Промышленные зоны
    RURAL = "rural"             # Сельская местность
    POLAR = "polar"             # Полярные регионы
    MIXED = "mixed"             # Смешанная местность


class ScoreTier(StrEnum):
    """Уровни очков"""
    PERFECT = "perfect"        # 4500-5000 очков
    EXCELLENT = "excellent"    # 3500-4499 очков
    GOOD = "good"              # 2500-3499 очков
    AVERAGE = "average"        # 1500-2499 очков
    POOR = "poor"              # 500-1499 очков
    BAD = "bad"                # 1-499 очков
    ZERO = "zero"              # 0 очков


class TimeControl(StrEnum):
    """Контроль времени"""
    UNLIMITED = "unlimited"    # Без ограничения времени
    STANDARD = "standard"      # Стандартное время (3 мин)
    RAPID = "rapid"            # Быстрые игры (1 мин)
    BLITZ = "blitz"            # Блиц (30 сек)
    BULLET = "bullet"          # Пуля (10 сек)


# Утилиты для работы с enum'ами
class EnumUtils:
    """Утилиты для работы с enum'ами"""
    
    @staticmethod
    def get_difficulty_display_name(difficulty: int) -> str:
        """Получить читаемое название уровня сложности"""
        difficulty_names = {
            1: "Очень легко",
            2: "Легко", 
            3: "Средне",
            4: "Сложно",
            5: "Очень сложно",
            6: "Эксперт",
            7: "Мастер"
        }
        return difficulty_names.get(difficulty, f"Уровень {difficulty}")
    
    @staticmethod
    def get_difficulty_color(difficulty: int) -> str:
        """Получить цвет для уровня сложности"""
        difficulty_colors = {
            1: "success",   # Зелёный
            2: "info",      # Голубой
            3: "primary",   # Синий
            4: "warning",   # Жёлтый
            5: "danger",    # Красный
            6: "dark",      # Тёмный
            7: "purple"     # Фиолетовый
        }
        return difficulty_colors.get(difficulty, "secondary")
    
    @staticmethod
    def get_category_display_name(category: str) -> str:
        """Получить читаемое название категории"""
        category_names = {
            ZoneCategory.CITY: "Город",
            ZoneCategory.NATURE: "Природа",
            ZoneCategory.COAST: "Побережье",
            ZoneCategory.MOUNTAINS: "Горы",
            ZoneCategory.DESERT: "Пустыня",
            ZoneCategory.ISLANDS: "Острова",
            ZoneCategory.HISTORICAL: "Историческое место",
            ZoneCategory.ARCHITECTURE: "Архитектура",
            ZoneCategory.INDUSTRIAL: "Промышленная зона",
            ZoneCategory.RURAL: "Сельская местность",
            ZoneCategory.POLAR: "Полярный регион",
            ZoneCategory.MIXED: "Смешанная местность",
        }
        return category_names.get(category, category)
    
    @staticmethod
    def get_score_tier(score: int) -> ScoreTier:
        """Определить уровень очков"""
        if score >= 4500:
            return ScoreTier.PERFECT
        elif score >= 3500:
            return ScoreTier.EXCELLENT
        elif score >= 2500:
            return ScoreTier.GOOD
        elif score >= 1500:
            return ScoreTier.AVERAGE
        elif score >= 500:
            return ScoreTier.POOR
        elif score > 0:
            return ScoreTier.BAD
        else:
            return ScoreTier.ZERO
    
    @staticmethod
    def get_score_tier_display_name(tier: ScoreTier) -> str:
        """Получить читаемое название уровня очков"""
        tier_names = {
            ScoreTier.PERFECT: "Идеально",
            ScoreTier.EXCELLENT: "Отлично",
            ScoreTier.GOOD: "Хорошо",
            ScoreTier.AVERAGE: "Средне",
            ScoreTier.POOR: "Плохо",
            ScoreTier.BAD: "Очень плохо",
            ScoreTier.ZERO: "Ноль очков",
        }
        return tier_names.get(tier, tier.value)
    
    @staticmethod
    def get_game_mode_display_name(mode: GameMode) -> str:
        """Получить читаемое название режима игры"""
        mode_names = {
            GameMode.SOLO: "Одиночная",
            GameMode.MULTIPLAYER: "Мультиплеер",
            GameMode.CHALLENGE: "Челлендж",
            GameMode.PRACTICE: "Тренировка",
        }
        return mode_names.get(mode, mode.value)
    
    @staticmethod
    def validate_difficulty(difficulty: int) -> bool:
        """Проверить корректность уровня сложности"""
        return 1 <= difficulty <= 7
    
    @staticmethod
    def get_difficulty_from_string(difficulty_str: str) -> int:
        """Получить числовой уровень сложности из строки"""
        difficulty_map = {
            "very_easy": 1,
            "easy": 2,
            "medium": 3,
            "hard": 4,
            "very_hard": 5,
            "expert": 6,
            "master": 7,
        }
        return difficulty_map.get(difficulty_str.lower(), 3)  # По умолчанию средний