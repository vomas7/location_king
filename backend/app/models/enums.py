"""Перечисления игровых моделей."""

from enum import StrEnum


class SessionStatus(StrEnum):
    """Статусы игровой сессии."""

    ACTIVE = "active"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class RoundStatus(StrEnum):
    """Статусы раунда."""

    ACTIVE = "active"
    GUESSED = "guessed"
    TIMED_OUT = "timed_out"


class MatchStatus(StrEnum):
    """Состояние комнаты мультиплеера."""

    OPEN = "open"  # можно присоединиться
    CLOSED = "closed"  # хост закрыл набор


class Continent(StrEnum):
    """Части света. Нужны для фильтра в меню."""

    EUROPE = "europe"
    ASIA = "asia"
    AFRICA = "africa"
    NORTH_AMERICA = "north_america"
    SOUTH_AMERICA = "south_america"
    OCEANIA = "oceania"
    ANTARCTICA = "antarctica"


class CountryGroup(StrEnum):
    """
    Страны и объединения стран для фильтра в меню.

    Отдельно от частей света: Евросоюз не совпадает с Европой, а Россия лежит
    сразу в двух частях света. Фильтры независимы, но в меню игрок выбирает
    что-то одно — пересечение вроде «Европа и Россия» не дало бы ни одной зоны.
    """

    RUSSIA = "russia"
    USA = "usa"
    EU = "eu"


class ZoneCategory(StrEnum):
    """Категории игровых зон."""

    CITY = "city"
    NATURE = "nature"
    COAST = "coast"
    MOUNTAINS = "mountains"
    DESERT = "desert"
    ISLANDS = "islands"
    HISTORICAL = "historical"
    ARCHITECTURE = "architecture"
    INDUSTRIAL = "industrial"
    RURAL = "rural"
    POLAR = "polar"
    MIXED = "mixed"


# Страны каждой группы — так, как они записаны в поле country игровой зоны.
# Перечислены все участники, а не только те, на которые сейчас есть зоны:
# новая зона попадёт в фильтр сама.
COUNTRY_GROUPS: dict[CountryGroup, tuple[str, ...]] = {
    CountryGroup.RUSSIA: ("Россия",),
    CountryGroup.USA: ("США",),
    CountryGroup.EU: (
        "Австрия",
        "Бельгия",
        "Болгария",
        "Венгрия",
        "Германия",
        "Греция",
        "Дания",
        "Ирландия",
        "Испания",
        "Италия",
        "Кипр",
        "Латвия",
        "Литва",
        "Люксембург",
        "Мальта",
        "Нидерланды",
        "Польша",
        "Португалия",
        "Румыния",
        "Словакия",
        "Словения",
        "Финляндия",
        "Франция",
        "Хорватия",
        "Чехия",
        "Швеция",
        "Эстония",
    ),
}

COUNTRY_GROUP_NAMES = {
    CountryGroup.RUSSIA: "Россия",
    CountryGroup.USA: "США",
    CountryGroup.EU: "Евросоюз",
}

CONTINENT_NAMES = {
    Continent.EUROPE: "Европа",
    Continent.ASIA: "Азия",
    Continent.AFRICA: "Африка",
    Continent.NORTH_AMERICA: "Северная Америка",
    Continent.SOUTH_AMERICA: "Южная Америка",
    Continent.OCEANIA: "Австралия и Океания",
    Continent.ANTARCTICA: "Антарктида",
}

DIFFICULTY_NAMES = {
    1: "Очень легко",
    2: "Легко",
    3: "Средне",
    4: "Сложно",
    5: "Очень сложно",
}

CATEGORY_NAMES = {
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


def difficulty_name(difficulty: int) -> str:
    """Читаемое название уровня сложности."""
    return DIFFICULTY_NAMES.get(difficulty, f"Уровень {difficulty}")


def category_name(category: str | None) -> str:
    """Читаемое название категории зоны."""
    if category is None:
        return CATEGORY_NAMES[ZoneCategory.MIXED]
    return CATEGORY_NAMES.get(ZoneCategory(category), category)


def group_countries(group: str) -> tuple[str, ...]:
    """Страны группы. Неизвестная группа — ошибка значения, а не пустой список."""
    return COUNTRY_GROUPS[CountryGroup(group)]


def continent_name(continent: str | None) -> str:
    """Читаемое название части света."""
    if continent is None:
        return "Не указано"
    return CONTINENT_NAMES.get(Continent(continent), continent)
