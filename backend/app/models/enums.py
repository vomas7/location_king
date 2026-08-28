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


class Difficulty(StrEnum):
    """
    Уровень партии — это выбор содержания, а не множитель очков.

    Легко — всемирно известные города, которые узнают по одной излучине реки.
    Средне — любой город и городской объект. Сложно — обжитая местность без
    города: поля, дельты, острова. Хардкор — дикая природа, где ориентиров нет
    вовсе и приходится читать рельеф.
    """

    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    HARDCORE = "hardcore"


class ZoneCollection(StrEnum):
    """
    Подборки мест — то, что не выводится из данных зоны.

    Крупный и известный город определяется не населением: Гуанчжоу больше
    Амстердама, но узнают с воздуха второй. Поэтому список составлен руками.
    """

    MAJOR_CITIES = "major_cities"


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

# Города, которые человек узнаёт, даже если никогда там не был: по излучине
# реки, по острову, по сетке улиц или по единственной в мире форме берега.
# Критерий — известность, а не размер, поэтому здесь нет ни Гуанчжоу, ни
# Шэньчжэня, зато есть Венеция и Монако.
ZONE_COLLECTIONS: dict[ZoneCollection, tuple[str, ...]] = {
    ZoneCollection.MAJOR_CITIES: (
        "Амстердам",
        "Афины",
        "Бангкок",
        "Барселона",
        "Берлин",
        "Будапешт",
        "Буэнос-Айрес",
        "Вена",
        "Венеция",
        "Гонконг",
        "Дубай",
        "Иерусалим",
        "Каир",
        "Кейптаун",
        "Копенгаген",
        "Куала-Лумпур",
        "Лас-Вегас",
        "Лиссабон",
        "Лондон",
        "Лос-Анджелес",
        "Мадрид",
        "Майами",
        "Мехико",
        "Милан",
        "Монако",
        "Москва, центр",
        "Мюнхен",
        "Нью-Йорк, Манхэттен",
        "Осака",
        "Париж",
        "Пекин",
        "Прага",
        "Рим",
        "Рио-де-Жанейро",
        "Сан-Франциско",
        "Санкт-Петербург",
        "Сеул",
        "Сидней",
        "Сингапур",
        "Стамбул",
        "Стокгольм",
        "Токио",
        "Торонто",
        "Чикаго",
        "Шанхай",
    ),
}

# Какие категории зон попадают на каждый уровень. «Легко» задаётся не
# категорией, а подборкой известных городов: Гуанчжоу — тоже город, но лёгким
# раундом он не будет.
DIFFICULTY_CATEGORIES: dict[Difficulty, tuple[str, ...]] = {
    Difficulty.NORMAL: ("city", "coast", "historical", "architecture", "industrial"),
    Difficulty.HARD: ("rural", "islands"),
    Difficulty.HARDCORE: ("nature", "mountains", "desert", "polar"),
}

DIFFICULTY_NAMES = {
    Difficulty.EASY: "Легко",
    Difficulty.NORMAL: "Средне",
    Difficulty.HARD: "Сложно",
    Difficulty.HARDCORE: "Хардкор",
}

ZONE_COLLECTION_NAMES = {
    ZoneCollection.MAJOR_CITIES: "Крупные города",
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


def category_name(category: str | None) -> str:
    """Читаемое название категории зоны."""
    if category is None:
        return CATEGORY_NAMES[ZoneCategory.MIXED]
    return CATEGORY_NAMES.get(ZoneCategory(category), category)


def group_countries(group: str) -> tuple[str, ...]:
    """Страны группы. Неизвестная группа — ошибка значения, а не пустой список."""
    return COUNTRY_GROUPS[CountryGroup(group)]


def collection_zones(collection: str) -> tuple[str, ...]:
    """Названия зон подборки."""
    return ZONE_COLLECTIONS[ZoneCollection(collection)]


def difficulty_categories(difficulty: str) -> tuple[str, ...]:
    """Категории зон уровня. Для «легко» пусто: он задаётся подборкой."""
    return DIFFICULTY_CATEGORIES.get(Difficulty(difficulty), ())


def continent_name(continent: str | None) -> str:
    """Читаемое название части света."""
    if continent is None:
        return "Не указано"
    return CONTINENT_NAMES.get(Continent(continent), continent)
