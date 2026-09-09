"""
Соперники-боты в дуэлях.

Дуэль ищет живого человека, но в игре, куда только начали приходить, очередь
чаще всего пустая: игрок нажимает «найти соперника» и упирается в тишину.
Бот закрывает эту дыру — с ним можно сыграть прямо сейчас.

Бот назван ботом. Он помечен флагом в учётной записи, значок стоит рядом с
именем везде, где его видно, и предлагается он словами «живых соперников
сейчас нет». Выдавать его за человека нельзя: игра держится на том, что её
числа настоящие, и один поддельный соперник стоит дороже пустой очереди.
Поэтому же бот не попадает ни в счётчик игроков, ни в таблицу лидеров, ни в
статистику зон — и не двигает рейтинг.

Промах бота не случаен. Случайная точка на Земле — это промах в среднем на
десять тысяч километров, то есть ноль очков в каждом раунде: с таким
соперником нельзя ни выиграть интересно, ни проиграть. Вместо этого бот
отталкивается от того, насколько люди обычно промахиваются именно на этом
месте — зона хранит своё среднее, — и отклоняется от него по своему уровню.
Так бот мажет на трудных местах и попадает на лёгких, как человек.
"""

import logging
import math
import random
import secrets
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.match import Match
from app.models.round import Round
from app.models.user import User
from app.observability import metrics
from app.services import auth as auth_service
from app.services import game as game_service
from app.services import matches as matches_service
from app.utils import avatar
from app.utils.geo import point_at_distance

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BotSpec:
    """Описание бота: как его зовут и насколько он хорош."""

    #: Служебное имя учётной записи. По нему бот находится и не заводится дважды
    username: str
    display_name: str
    #: Насколько бот точнее среднего игрока, от нуля до единицы. Половина —
    #: ровно средний игрок, единица — заметно лучше, ноль — заметно хуже
    skill: float
    #: Рейтинг: по нему бот подбирается под уровень игрока
    rating: int


#: Пятеро соперников. Разный уровень нужен, чтобы игроку было с кем играть и
#: в первый день, и через месяц: слабый бот перестаёт быть интересен быстро,
#: а сильный отбивает желание начинать
BOTS: tuple[BotSpec, ...] = (
    BotSpec("bot-compass", "Компас", skill=0.15, rating=900),
    BotSpec("bot-atlas", "Атлас", skill=0.35, rating=1050),
    BotSpec("bot-meridian", "Меридиан", skill=0.5, rating=1200),
    BotSpec("bot-sextant", "Секстант", skill=0.7, rating=1350),
    BotSpec("bot-polaris", "Полярная", skill=0.9, rating=1500),
)

#: Во сколько раз бот промахивается сильнее среднего игрока при нулевом
#: уровне и во сколько раз точнее при единице. Средний игрок — это единица,
#: и он приходится ровно на половину шкалы
WORST_FACTOR = 3.0
BEST_FACTOR = 0.25

#: Разброс вокруг своего уровня. Без него бот выдавал бы один и тот же промах
#: на одном и том же месте, и партия против него читалась бы наизусть со
#: второго раза
SPREAD = 0.55

#: Насколько промахиваются там, где статистики ещё нет. Половина кадра: место
#: видно целиком, и типичная ошибка — соседний район, а не соседний континент
UNKNOWN_MISS_FRACTION = 0.5

#: Ближе этого бот не ставит точку. Ноль километров означал бы попадание в
#: пиксель, чего не бывает и у лучших игроков
CLOSEST_KM = 0.2


def enabled() -> bool:
    """Включены ли боты. Выключаются одной настройкой, когда станут не нужны."""
    return settings.duel_bots_enabled


def miss_for(typical_km: float, skill: float, rng: random.Random) -> float:
    """
    На сколько километров промахнётся бот такого уровня.

    Считается от того, насколько промахиваются люди на этом месте: уровень
    сдвигает это число, разброс не даёт партии повторяться. Разброс
    логнормальный, а не равномерный, — промахи людей устроены так же: чаще
    около своего обычного, изредка сильно мимо.
    """
    factor = WORST_FACTOR + (BEST_FACTOR - WORST_FACTOR) * min(max(skill, 0.0), 1.0)
    spread = math.exp(rng.gauss(0.0, SPREAD))

    return max(typical_km * factor * spread, CLOSEST_KM)


def typical_miss_km(zone: LocationZone | None, view_extent_km: float) -> float:
    """
    Насколько обычно промахиваются на этом месте.

    Среднее по зоне — настоящая статистика живых игроков, и она уже посчитана.
    Пока раундов на зоне не было, берётся доля кадра.
    """
    if zone is not None and zone.average_distance is not None and zone.average_distance > 0:
        return float(zone.average_distance)

    return view_extent_km * UNKNOWN_MISS_FRACTION


async def ensure(db: AsyncSession) -> list[User]:
    """
    Завести ботов, которых ещё нет, и вернуть всех.

    Пароля у бота нет: в поле лежит хеш от случайной строки, которую никто не
    видел, — войти под ним нельзя. Учётная запись нужна только затем, чтобы он
    мог занять место в комнате.
    """
    existing = {user.username for user in await all_bots(db)}
    created: list[User] = []

    for spec in BOTS:
        if spec.username in existing:
            continue

        user = User(
            username=spec.username,
            email=f"{spec.username}@bots.invalid",
            password_hash=auth_service.hash_password(secrets.token_hex(24)),
            display_name=spec.display_name,
            friend_code=await auth_service.unique_friend_code(db),
            rating=spec.rating,
            is_bot=True,
        )
        db.add(user)
        created.append(user)

    if created:
        await db.flush()

        # Узор выводится из идентификатора, а он известен только после записи —
        # тем же способом, что и у людей
        for user in created:
            user.avatar_shape, user.avatar_color = avatar.default_for(user.id)

        await db.flush()
        logger.info("Заведены соперники-боты: %s", [user.username for user in created])

    return await all_bots(db)


async def all_bots(db: AsyncSession) -> list[User]:
    """Все боты, какие есть в базе, от слабого к сильному."""
    stmt = select(User).where(User.is_bot.is_(True)).order_by(User.rating)
    return list((await db.execute(stmt)).scalars().all())


async def available(db: AsyncSession) -> int:
    """Сколько соперников-ботов готовы сыграть прямо сейчас."""
    if not enabled():
        return 0

    stmt = select(func.count()).select_from(User).where(User.is_bot.is_(True))
    return int((await db.execute(stmt)).scalar_one())


async def pick(db: AsyncSession, rating: int) -> User | None:
    """
    Бот под уровень игрока: ближайший по рейтингу.

    Ближайший, а не случайный: дуэль с соперником своего уровня — это игра, а
    с чужим — либо разгром, либо издевательство.
    """
    if not enabled():
        return None

    bots = await all_bots(db)
    if not bots:
        return None

    return min(bots, key=lambda bot: abs(bot.rating - rating))


async def play(db: AsyncSession, match: Match, bot: User) -> GameSession:
    """
    Прогнать бота по серии дуэли целиком.

    Бот отыгрывает всю партию сразу: думающего над раундом соперника здесь
    нет, а растягивать ответы во времени ради видимости значило бы держать
    игрока в ожидании впустую.

    Отвечает он тем же кодом, что и человек: те же раунды серии, тот же
    подсчёт очков. Своей арифметики у бота нет — иначе дуэль с ним меряла бы
    не то же самое, что дуэль с человеком.
    """
    session, first = await matches_service.join(db, match, bot)
    rng = random.Random()

    round_obj: Round | None = first
    while round_obj is not None:
        point = await _guess_for(db, round_obj, bot, rng)
        _, round_obj = await game_service.submit_guess(db, bot, round_obj, point=point)

    await metrics.count("duel_bot_played")
    logger.info(
        "Бот %s отыграл дуэль %s со счётом %s", bot.username, match.code, session.total_score
    )

    return session


async def _guess_for(
    db: AsyncSession, round_obj: Round, bot: User, rng: random.Random
) -> tuple[float, float]:
    """Куда бот поставит точку в этом раунде."""
    target_lon, target_lat = await game_service.target_coordinates(db, round_obj)
    zone = await db.get(LocationZone, round_obj.zone_id)

    typical = typical_miss_km(zone, float(round_obj.view_extent_km))
    distance = miss_for(typical, skill_of(bot), rng)

    return point_at_distance(target_lon, target_lat, distance, rng.uniform(0, 360))


def skill_of(bot: User) -> float:
    """
    Уровень бота по его учётной записи.

    Бот из базы, которого нет в списке, остался от прежней версии: он играет
    как средний игрок — это честнее, чем не играть вовсе.
    """
    spec = next((item for item in BOTS if item.username == bot.username), None)

    return 0.5 if spec is None else spec.skill
