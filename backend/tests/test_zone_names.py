"""
Каталог и таблица переводов не должны расходиться.

Каталог правят руками: добавили город — и в английской игре он останется
кириллицей, пока кто-нибудь не заметит. Замечает этот тест: он читает
`scripts/seed.py` и требует перевод для каждого названия, каждого региона и
каждой страны каталога.

Отдельный файл читается, а не импортируется вместе с seed: сам скрипт при
импорте ничего не делает, но зависеть от этого не хочется.
"""

import re
from pathlib import Path

import pytest

from app.models.enums import CATEGORY_NAMES, CONTINENT_NAMES, category_name, continent_name
from app.utils.zone_names import PLACE_NAMES, country_name, place_name

SEED = Path(__file__).resolve().parents[1] / "scripts" / "seed.py"


def catalog() -> str:
    return SEED.read_text(encoding="utf-8")


def names() -> set[str]:
    return set(re.findall(r'\n        name="([^"]+)"', catalog()))


def regions() -> set[str]:
    return set(re.findall(r'region="([^"]+)"', catalog()))


def countries() -> set[str]:
    return set(re.findall(r'country="([^"]+)"', catalog()))


def test_catalog_is_read() -> None:
    """Если разбор сломается, остальные проверки станут пустыми."""
    assert len(names()) > 250
    assert len(regions()) > 200
    assert len(countries()) > 50


def test_every_zone_has_an_english_name() -> None:
    assert sorted(names() - set(PLACE_NAMES)) == []


def test_every_region_has_an_english_name() -> None:
    assert sorted(regions() - set(PLACE_NAMES)) == []


def test_every_country_of_the_catalog_is_translated() -> None:
    """Страна каталога называется по-русски, а таблица знает её по коду ISO."""
    untranslated = sorted(name for name in countries() if country_name(name, "en") == name)
    assert untranslated == []


def test_translations_are_not_the_russian_name_again() -> None:
    """Кириллица в английской колонке — это забытый перевод."""
    cyrillic = sorted(value for value in PLACE_NAMES.values() if re.search(r"[А-Яа-я]", value))
    assert cyrillic == []


def test_names_are_left_alone_on_russian() -> None:
    assert place_name("Москва", "ru") == "Москва"
    assert country_name("Япония", "ru") == "Япония"


def test_names_are_translated_on_english() -> None:
    assert place_name("Москва", "en") == "Moscow"
    assert place_name("Иль-де-Франс", "en") == "Île-de-France"
    assert country_name("Япония", "en") == "Japan"


def test_unknown_place_is_shown_as_it_is() -> None:
    """Новое место без перевода показываем по-русски, а не прячем."""
    assert place_name("Зеленоградск", "en") == "Зеленоградск"
    assert place_name(None, "en") is None


@pytest.mark.parametrize("category", sorted(CATEGORY_NAMES))
def test_category_speaks_both_languages(category: str) -> None:
    assert category_name(category, "ru") != category_name(category, "en")


@pytest.mark.parametrize("continent", sorted(CONTINENT_NAMES))
def test_continent_speaks_both_languages(continent: str) -> None:
    assert continent_name(continent, "ru") != continent_name(continent, "en")
