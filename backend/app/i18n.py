"""
На каком языке отвечать этому запросу.

Язык называет клиент заголовком `Accept-Language`: интерфейс переключается
в браузере, а не в профиле, и заголовок — единственное место, где сервер
может об этом узнать. Разбираем только первый тег и только до дефиса: «en-GB»
и «en» для игры одно и то же, а списка языков с весами у нас всё равно два.

Русский — язык по умолчанию: игра русская, и запрос без заголовка приходит
скорее от неё же.
"""

from fastapi import Request

#: Языки, на которых игра умеет отвечать
LANGUAGES = ("ru", "en")

DEFAULT_LANGUAGE = "ru"


def language_of(request: Request) -> str:
    """Язык запроса. Незнакомый или отсутствующий — русский."""
    header = request.headers.get("accept-language", "")
    first = header.split(",")[0].strip().split("-")[0].lower()

    return first if first in LANGUAGES else DEFAULT_LANGUAGE
