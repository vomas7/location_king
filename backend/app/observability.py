"""
Наблюдаемость: идентификатор запроса, структурные логи и счётчики.

Метрики собираются в процессе и отдаются в формате Prometheus без
дополнительной зависимости: набор показателей маленький, а тянуть ради него
библиотеку незачем. Если показателей станет больше, здесь появится
prometheus-client, и это будет отдельным решением.
"""

import logging
import time
import uuid
from collections import Counter
from contextvars import ContextVar
from dataclasses import dataclass, field

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)

#: Идентификатор текущего запроса. Попадает в каждую строку лога и в ответ,
#: чтобы жалобу игрока можно было найти в логах по одному числу.
request_id: ContextVar[str] = ContextVar("request_id", default="-")

REQUEST_ID_HEADER = "X-Request-ID"

# Границы гистограммы задержек, секунды
LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


@dataclass
class Metrics:
    """Счётчики за время жизни процесса."""

    requests: Counter[tuple[str, str, int]] = field(default_factory=Counter)
    latency_buckets: Counter[tuple[str, float]] = field(default_factory=Counter)
    latency_sum: Counter[str] = field(default_factory=Counter)
    events: Counter[str] = field(default_factory=Counter)

    def observe_request(self, method: str, route: str, status: int, seconds: float) -> None:
        self.requests[method, route, status] += 1
        self.latency_sum[route] += seconds

        for bucket in LATENCY_BUCKETS:
            if seconds <= bucket:
                self.latency_buckets[route, bucket] += 1

    def count(self, event: str) -> None:
        """Отметить событие: попадание в кэш, поход к провайдеру и подобное."""
        self.events[event] += 1

    def render(self) -> str:
        """Показатели в текстовом формате Prometheus."""
        lines = [
            "# HELP location_king_requests_total Обработанные запросы",
            "# TYPE location_king_requests_total counter",
        ]
        for (method, route, status), value in sorted(self.requests.items()):
            lines.append(
                f'location_king_requests_total{{method="{method}",route="{route}",'
                f'status="{status}"}} {value}'
            )

        lines += [
            "# HELP location_king_request_seconds Время обработки запроса",
            "# TYPE location_king_request_seconds histogram",
        ]
        for (route, bucket), value in sorted(self.latency_buckets.items()):
            lines.append(
                f'location_king_request_seconds_bucket{{route="{route}",le="{bucket}"}} {value}'
            )
        for route, total in sorted(self.latency_sum.items()):
            lines.append(f'location_king_request_seconds_sum{{route="{route}"}} {total:.3f}')

        lines += [
            "# HELP location_king_events_total Внутренние события",
            "# TYPE location_king_events_total counter",
        ]
        for event, value in sorted(self.events.items()):
            lines.append(f'location_king_events_total{{event="{event}"}} {value}')

        return "\n".join(lines) + "\n"


metrics = Metrics()


class RequestIdFilter(logging.Filter):
    """Подмешивает идентификатор запроса в каждую строку лога."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Присваивает запросу идентификатор, считает время и статус."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        current = incoming or uuid.uuid4().hex[:12]
        token = request_id.set(current)

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Ошибку залогирует обработчик выше, но в метрики она попасть должна
            metrics.observe_request(
                request.method,
                _route_of(request),
                500,
                time.perf_counter() - started,
            )
            logger.exception("Запрос %s %s упал", request.method, request.url.path)
            raise
        finally:
            # Сбрасывать нужно после того, как идентификатор попал в заголовок,
            # иначе в ответ уедет значение по умолчанию
            request_id.reset(token)

        elapsed = time.perf_counter() - started
        metrics.observe_request(request.method, _route_of(request), response.status_code, elapsed)
        response.headers[REQUEST_ID_HEADER] = current

        return response


def _route_of(request: Request) -> str:
    """
    Шаблон пути, а не сам путь.

    Иначе каждый тайл и каждая партия завели бы собственную метрику, и их стало
    бы больше, чем запросов.
    """
    route = request.scope.get("route")
    path = getattr(route, "path", None)

    return path if isinstance(path, str) else "unknown"


def configure_logging(debug: bool) -> None:
    """Настроить логи так, чтобы в каждой строке был идентификатор запроса."""
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s")
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if debug else logging.INFO)
