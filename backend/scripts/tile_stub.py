#!/usr/bin/env python3
"""
Заглушка тайлового сервера для сквозных сценариев.

Настоящий провайдер снимков в тестах не нужен: сценарии проверяют игру, а не
картинку, и зависеть от чужой доступности им незачем. Отдаёт JPEG с
координатами тайла, чтобы на скриншотах падений было видно, что именно
запрашивалось.

    python scripts/tile_stub.py --port 8899
"""

import argparse
import colorsys
import io
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image, ImageDraw

logger = logging.getLogger("tile-stub")

TILE_PATH = re.compile(r"^/tile/(\d+)/(\d+)/(\d+)$")
TILE_SIZE = 256


def render(z: int, x: int, y: int) -> bytes:
    """Цветной квадрат с подписью координат."""
    hue = ((x * 7 + y * 13 + z * 29) % 360) / 360
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.35, 0.55)

    image = Image.new(
        "RGB", (TILE_SIZE, TILE_SIZE), (int(red * 255), int(green * 255), int(blue * 255))
    )
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, TILE_SIZE - 1, TILE_SIZE - 1], outline=(255, 255, 255), width=2)
    draw.text((14, 14), f"z={z}\nx={x}\ny={y}", fill=(255, 255, 255))

    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=70)
    return buffer.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        """Тихо: иначе лог сценария тонет в запросах тайлов."""

    def do_GET(self) -> None:
        match = TILE_PATH.match(self.path)
        if match is None:
            self.send_error(404)
            return

        zoom, tile_y, tile_x = (int(value) for value in match.groups())
        body = render(zoom, tile_x, tile_y)

        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Заглушка тайлового сервера")
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    logger.info("Тайлы отдаются на порту %s", args.port)

    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
