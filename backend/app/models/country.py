from geoalchemy2 import Geometry
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Country(Base):
    """
    Границы страны.

    Нужны режиму «угадай страну»: игрок ставит точку так же, как обычно, а
    сервер сам решает, в какую страну он попал. Считать это на клиенте
    означало бы отдать ему границы целиком — два мегабайта, которые к тому же
    подсказывают ответ.

    Данные из OpenStreetMap (ODbL), загружаются scripts/load_countries.py.
    """

    __tablename__ = "countries"

    #: Код ISO 3166-1 alpha-3. Он же ключ: имена стран меняются, коды — нет
    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    border: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Country {self.code} {self.name!r}>"
