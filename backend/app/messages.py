"""
Сообщения об ошибках на двух языках.

Сервер сам решает, на каком языке отвечать: клиент называет свой язык
заголовком `Accept-Language`, а обработчик ошибок в `main.py` берёт из
сообщения нужную сторону. Так игрок читает отказ на том же языке, на котором
читает всё остальное, и клиенту не приходится держать вторую копию тех же
формулировок.

Сообщения лежат здесь все сразу, а не рядом с местом, где брошены: так видно
сразу, что игра вообще умеет отвечать, и легко заметить два разных текста про
одно и то же.

Русский текст остаётся в исключении и уходит в журнал — читать логи на двух
языках было бы мучением.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    """Одно сообщение на двух языках."""

    ru: str
    en: str

    def format(self, **params: object) -> "Message":
        """Подставить значения в обе стороны сразу."""
        return Message(self.ru.format(**params), self.en.format(**params))

    def text(self, language: str) -> str:
        """Текст на выбранном языке. Незнакомый язык получает русский."""
        return self.en if language == "en" else self.ru


# Авторизация и учётная запись
TOKEN_INVALID = Message("Токен недействителен или истёк", "The token is invalid or has expired")
TOKEN_WRONG_TYPE = Message("Ожидался токен типа {expected}", "Expected a {expected} token")
TOKEN_WITHOUT_USER = Message(
    "Токен не содержит идентификатор пользователя", "The token carries no user id"
)
TOKEN_BROKEN_USER = Message(
    "Идентификатор пользователя в токене испорчен", "The user id in the token is broken"
)
AUTH_REQUIRED = Message("Требуется авторизация", "Authorisation required")
WRONG_CREDENTIALS = Message("Неверный email или пароль", "Wrong email or password")
WRONG_PASSWORD = Message("Неверный пароль", "Wrong password")
ACCOUNT_DISABLED = Message("Учётная запись отключена", "The account is disabled")
USER_GONE = Message("Пользователь не найден или отключён", "The user is missing or disabled")
EMAIL_TAKEN = Message(
    "Пользователь с таким email уже зарегистрирован",
    "A user with this email is already registered",
)
NAME_TOO_SHORT = Message(
    "Имя короче {least} символов", "The name is shorter than {least} characters"
)
NAME_TOO_LONG = Message("Имя длиннее {most} символов", "The name is longer than {most} characters")
NAME_LOOKS_LIKE_EMAIL = Message(
    "Имя с собакой похоже на адрес почты — его видят все игроки",
    "A name with an @ looks like an email address, and every player sees it",
)
NAME_BAD_CHARACTERS = Message(
    "В имени можно использовать буквы, цифры, пробел, дефис и точку",
    "The name may contain letters, digits, spaces, hyphens and dots",
)
NO_SUCH_AVATAR = Message("Такой аватарки нет", "There is no such avatar")
NO_PLAYER_CODE = Message(
    "Не удалось подобрать свободный код игрока", "Could not find a free player code"
)

# Картинка аватарки
FILE_EMPTY = Message("Файл пустой", "The file is empty")
FILE_TOO_BIG = Message("Файл больше {limit} МБ", "The file is larger than {limit} MB")
NOT_AN_IMAGE = Message(
    "Это не картинка или файл повреждён", "This is not an image, or the file is damaged"
)
UNSUPPORTED_IMAGE = Message("Подойдёт JPEG, PNG, WebP или GIF", "JPEG, PNG, WebP or GIF will do")
IMAGE_TOO_LARGE = Message("Картинка слишком большая", "The image is too large")
NO_UPLOADED_AVATAR = Message(
    "У этого игрока нет загруженной аватарки", "This player has no uploaded avatar"
)

# Серия и зоны
ROUNDS_OUT_OF_RANGE = Message(
    "Раундов в серии должно быть от {least} до {most}",
    "A series takes from {least} to {most} rounds",
)
SERIES_NOT_FOUND = Message("Серия {id} не найдена", "Series {id} not found")
SESSION_WITHOUT_SERIES = Message("Партия не привязана к серии", "The game is not tied to a series")
ROUND_NOT_IN_SERIES = Message(
    "В серии {series} нет раунда {position}", "Series {series} has no round {position}"
)
ZONE_ALL_WATER = Message("Зона {zone} целиком в воде", "Zone {zone} is entirely water")
ZONE_NOT_FOR_COUNTRIES = Message(
    "Зона {zone} не годится для режима стран", "Zone {zone} does not fit the country mode"
)
ZONE_NOT_FOR_CHOICE = Message(
    "Зона {zone} не годится для режима выбора", "Zone {zone} does not fit the choice mode"
)
NO_PLACE_FOR_CONDITIONS = Message(
    "Не нашлось подходящего места под заданные условия",
    "No place fits the conditions you have chosen",
)
NO_ZONES_FOR_CONDITIONS = Message(
    "Нет активных зон под заданные условия", "No active zones fit the conditions"
)
ZONE_NOT_FOUND = Message("Зона {id} не найдена", "Zone {id} not found")
ZONE_EMPTY_POLYGON = Message(
    "Не удалось выбрать точку в зоне {id}: полигон пуст",
    "Could not pick a point in zone {id}: the polygon is empty",
)

# Партия и раунд
GUESS_ALREADY_TAKEN = Message(
    "Догадка по этому раунду уже принята", "The guess for this round is already in"
)
SESSION_FINISHED = Message("Сессия уже завершена", "The game is already over")
SESSION_NOT_FOUND = Message("Сессия {id} не найдена", "Game {id} not found")
SESSION_OF_ANOTHER = Message("Это чужая сессия", "This game belongs to another player")
ROUND_NOT_FOUND = Message("Раунд {id} не найден", "Round {id} not found")
ROUND_OF_ANOTHER = Message("Это чужой раунд", "This round belongs to another player")
ROUND_CLOSED = Message("Раунд уже закрыт", "The round is already closed")
ROUND_TIME_LEFT = Message("Время ещё не вышло", "There is still time left")
ROUND_TIME_OVER = Message("Время раунда вышло", "The round is out of time")
ANSWER_WITH_PIN = Message(
    "В этом раунде отвечают точкой на карте", "This round is answered with a pin on the map"
)
ANSWER_WITH_COUNTRY = Message(
    "В этом раунде отвечают страной", "This round is answered with a country"
)
CHOICE_NOT_OFFERED = Message(
    "Такого варианта в этом раунде не предлагали", "This round did not offer that option"
)
NO_SUCH_COUNTRY = Message("Такой страны нет", "There is no such country")

# Знакомство с игрой без учётной записи
DEMO_ROUND_NOT_FOUND = Message("Такого раунда в знакомстве нет", "No such round in the demo")
DEMO_PLACE_MISSING = Message(
    "Места {place} нет в каталоге", "The place {place} is missing from the catalogue"
)
DEMO_PLACE_NOT_FOR_COUNTRIES = Message(
    "Место {place} разошлось с границами стран",
    "The place {place} does not line up with country borders",
)

# Подсказка
HINT_ALREADY_TAKEN = Message(
    "Подсказка по этому раунду уже взята", "The hint for this round is already taken"
)
HINT_ADDS_NOTHING = Message(
    "Подсказка ничего не добавит к условиям партии",
    "The hint would add nothing to the conditions of this game",
)

# Челлендж, комнаты и дуэли
DAILY_ALREADY_PLAYED = Message(
    "Челлендж этого дня уже сыгран", "Today's challenge has already been played"
)
NO_ROOM_CODE = Message(
    "Не удалось подобрать свободный код комнаты", "Could not find a free room code"
)
ROOM_NOT_FOUND = Message("Комната {code} не найдена", "Room {code} not found")
ROOM_CLOSED = Message("Набор в эту комнату закрыт", "This room is closed for new players")
ROOM_ALREADY_PLAYED = Message("Ты уже играл в этой комнате", "You have already played in this room")
ROOM_NOT_HOST = Message(
    "Закрыть комнату может только тот, кто её создал", "Only the host can close the room"
)
DUEL_NOT_FOUND = Message("Дуэль {code} не найдена", "Duel {code} not found")
DUEL_UNFINISHED = Message("Сначала доиграй начатую дуэль", "Finish the duel you started first")

# Друзья
FRIEND_CODE_UNKNOWN = Message("Игрока с таким кодом нет", "There is no player with this code")
FRIEND_CODE_OWN = Message("Это твой собственный код", "This is your own code")
FRIEND_ALREADY = Message("Вы уже друзья", "You are friends already")
FRIEND_REQUEST_SENT = Message("Заявка уже отправлена", "The request is already sent")
FRIEND_REQUEST_YOURS = Message(
    "Эту заявку отправил ты — ждать ответа тебе", "You sent this request — the answer is theirs"
)
FRIEND_REQUEST_UNKNOWN = Message("Такой заявки нет", "There is no such request")
FRIENDS_BOARD_PRIVATE = Message(
    "Зачёт среди друзей — только для своих", "The friends standing is for friends only"
)

# Снимки
TILE_ZOOM_OUTSIDE = Message(
    "Уровень {zoom} за пределами раунда", "Zoom {zoom} is outside the round"
)
TILE_OUTSIDE = Message("Тайл {x}/{y} за пределами раунда", "Tile {x}/{y} is outside the round")
PROVIDER_UNAVAILABLE = Message(
    "Провайдер снимков недоступен", "The imagery provider is unavailable"
)
PROVIDER_NOT_AN_IMAGE = Message(
    "Провайдер снимков вернул не картинку",
    "The imagery provider returned something else than an image",
)

# Частота запросов
TOO_OFTEN = Message(
    "Слишком часто. Разрешено {limit} за {minutes} мин, попробуй позже",
    "Too often. The limit is {limit} per {minutes} min, try later",
)
TOO_OFTEN_WINDOW = Message(
    "Слишком часто. Разрешено {limit} за окно, попробуй позже",
    "Too often. The limit is {limit} per window, try later",
)
