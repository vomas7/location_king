"""
На каком языке отвечает сервер.

Интерфейс переключается в браузере, а не в профиле, поэтому язык приезжает
заголовком запроса. Русский остаётся языком по умолчанию: игра русская, и
запрос без заголовка приходит скорее от неё.
"""

import re

import pytest
from httpx import AsyncClient

from app import messages
from app.i18n import DEFAULT_LANGUAGE, LANGUAGES
from app.messages import Message
from app.models.round import Round
from app.services import views
from app.utils import country_names
from app.utils.country_names import COUNTRY_NAMES

#: Все сообщения каталога
ALL = [value for value in vars(messages).values() if isinstance(value, Message)]


def placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", text))


def test_catalog_is_not_empty() -> None:
    assert len(ALL) > 40


@pytest.mark.parametrize("message", ALL)
def test_both_sides_are_filled(message: Message) -> None:
    assert message.ru.strip() != ""
    assert message.en.strip() != ""


@pytest.mark.parametrize("message", ALL)
def test_english_is_a_translation_and_not_a_copy(message: Message) -> None:
    """Незаполненный перевод выглядит как русский текст, скопированный целиком."""
    assert message.en != message.ru


@pytest.mark.parametrize("message", ALL)
def test_both_sides_take_the_same_values(message: Message) -> None:
    """Подстановка одна на два языка: разъехавшиеся имена уронили бы format."""
    assert placeholders(message.ru) == placeholders(message.en)


def test_unknown_language_falls_back_to_russian() -> None:
    message = Message("Русский", "English")

    assert message.text("ru") == "Русский"
    assert message.text("en") == "English"
    assert message.text("de") == "Русский"


def test_format_fills_both_sides() -> None:
    filled = Message("Зона {id}", "Zone {id}").format(id=7)

    assert filled.ru == "Зона 7"
    assert filled.en == "Zone 7"


def test_default_language_is_listed() -> None:
    assert DEFAULT_LANGUAGE in LANGUAGES


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, messages.WRONG_CREDENTIALS.ru),
        ("ru", messages.WRONG_CREDENTIALS.ru),
        ("en", messages.WRONG_CREDENTIALS.en),
        # Диалект — тот же язык: «en-GB» и «en» для игры одно и то же
        ("en-GB,en;q=0.9", messages.WRONG_CREDENTIALS.en),
        # Незнакомый язык получает русский, а не пустое место
        ("de", messages.WRONG_CREDENTIALS.ru),
    ],
)
async def test_error_speaks_the_language_of_the_request(
    client: AsyncClient, header: str | None, expected: str
) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever-long-enough"},
        headers={} if header is None else {"Accept-Language": header},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == expected


@pytest.mark.parametrize("code", sorted(COUNTRY_NAMES))
def test_country_is_named_on_both_languages(code: str) -> None:
    known = COUNTRY_NAMES[code]

    assert known.ru.strip() != ""
    assert known.en.strip() != ""
    # Кириллица и латиница совпасть не могут: одинаковые строки означают, что
    # перевод забыли и в таблицу попало русское имя дважды
    assert known.ru != known.en


def test_unknown_country_shows_its_code() -> None:
    """Код из границ без имени — это всё-таки страна, и молчать о ней нельзя."""
    assert country_names.name_of("ZZZ", "en") == "ZZZ"
    assert country_names.name_of(None, "en") is None


def test_country_is_named_in_the_language_of_the_request() -> None:
    assert country_names.name_of("FRA", "ru") == "Франция"
    assert country_names.name_of("FRA", "en") == "France"


def test_choices_are_named_in_the_language_of_the_request() -> None:
    """Варианты ответа собираются из кодов, и порядок при этом сохраняется."""
    round_obj = Round(choices="FRA,ESP,DEU")

    assert views.choice_names(round_obj, "ru") == [
        ("FRA", "Франция"),
        ("ESP", "Испания"),
        ("DEU", "Германия"),
    ]
    assert views.choice_names(round_obj, "en") == [
        ("FRA", "France"),
        ("ESP", "Spain"),
        ("DEU", "Germany"),
    ]
