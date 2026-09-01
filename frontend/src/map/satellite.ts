/**
 * Карта спутникового снимка раунда.
 *
 * Живёт в пиксельной проекции: у неё нет ни широты, ни долготы, только
 * локальная сетка тайлов, которую переводит сервер. Клиент физически не может
 * узнать, где находится показанное место.
 *
 * Локальная сетка — квадродерево с корнем в тайле раунда: уровень z содержит
 * 2^z × 2^z тайлов, каждый совпадает с тайлом провайдера на зуме tile_zoom + z.
 */

import type { Map as OlMap } from "ol";
import MapBrowser from "ol/Map";
import View from "ol/View";
import Feature from "ol/Feature";
import TileState from "ol/TileState";
import Point from "ol/geom/Point";
import TileLayer from "ol/layer/Tile";
import VectorLayer from "ol/layer/Vector";
import Projection from "ol/proj/Projection";
import VectorSource from "ol/source/Vector";
import XYZ from "ol/source/XYZ";
import TileGrid from "ol/tilegrid/TileGrid";
import { defaults as defaultControls } from "ol/control/defaults";
import type ImageTile from "ol/ImageTile";

import { authorizedFetch, tileUrl } from "~/api/client";
import type { RoundView } from "~/api/types";
import { STYLE_CENTER } from "~/map/styles";

const TILE_SIZE = 256;

/** Сколько ждать перед повторной попыткой загрузить тайл, мс. */
const RETRY_DELAY_MS = 700;

export interface SatelliteMap {
  readonly map: OlMap;
  /** Вернуть вид к исходному масштабу, показывающему участок целиком. */
  reset: () => void;
  /** Вернуть север наверх, не трогая ни центр, ни масштаб. */
  straighten: () => void;
  destroy: () => void;
}

/** О чём карта сообщает наружу, пока игрок её крутит и таскает. */
export interface SatelliteEvents {
  /** Часть снимка не загрузилась — или, наоборот, догрузилась. */
  onMissingTiles: (missing: boolean) => void;
  /** Снимок повёрнут: север больше не наверху. */
  onRotated: (rotated: boolean) => void;
}

/** Отметить тайл как загруженный или как не загрузившийся. */
type TrackTile = (key: string, failed: boolean) => void;

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Загрузка тайла с заголовком авторизации.
 *
 * Обычный <img src> заголовки не отправляет, поэтому тайл забирается через
 * fetch и подставляется как blob.
 *
 * Неудачу не считаем окончательной с первого раза: мобильная сеть рвётся на
 * секунду, а обновлённый токен доступа приезжает не мгновенно.
 */
function loadTile(track: TrackTile) {
  const fetchTile = async (src: string): Promise<Blob | null> => {
    try {
      const response = await authorizedFetch(src);
      return response.ok ? await response.blob() : null;
    } catch {
      return null;
    }
  };

  return (tile: ImageTile, src: string): void => {
    const key = tile.getTileCoord().join("/");

    void (async () => {
      let blob = await fetchTile(src);

      if (blob === null) {
        await wait(RETRY_DELAY_MS);
        blob = await fetchTile(src);
      }

      if (blob === null) {
        tile.setState(TileState.ERROR);
        track(key, true);
        return;
      }

      const objectUrl = URL.createObjectURL(blob);
      const image = tile.getImage() as HTMLImageElement;

      image.onload = () => {
        URL.revokeObjectURL(objectUrl);
        track(key, false);
      };
      image.onerror = () => {
        URL.revokeObjectURL(objectUrl);
        tile.setState(TileState.ERROR);
        track(key, true);
      };
      image.src = objectUrl;
    })();
  };
}

export function createSatelliteMap(
  target: HTMLElement,
  round: RoundView,
  { onMissingTiles, onRotated }: SatelliteEvents,
): SatelliteMap {
  // Считаем именно текущие дыры в снимке, а не то, была ли ошибка когда-либо:
  // подгрузившийся тайл убирает себя отсюда, и предупреждение исчезает само
  const missing = new Set<string>();

  const track: TrackTile = (key, failed) => {
    const before = missing.size;

    if (failed) {
      missing.add(key);
    } else {
      missing.delete(key);
    }

    if (missing.size !== before) onMissingTiles(missing.size > 0);
  };

  const size = TILE_SIZE * 2 ** round.max_zoom;
  const extent: [number, number, number, number] = [0, -size, size, 0];
  const center: [number, number] = [size / 2, -size / 2];

  const projection = new Projection({
    code: `round:${String(round.id)}`,
    units: "pixels",
    extent,
  });

  const source = new XYZ({
    projection,
    tileGrid: new TileGrid({
      extent,
      origin: [0, 0],
      resolutions: Array.from({ length: round.max_zoom + 1 }, (_, z) => 2 ** (round.max_zoom - z)),
      tileSize: TILE_SIZE,
    }),
    // Координата тайла приходит как кортеж [z, x, y]; noUncheckedIndexedAccess
    // делает элементы возможно-неопределёнными, поэтому подставляем нули
    tileUrlFunction: ([z = 0, x = 0, y = 0]) => tileUrl(round.tiles_url, z, x, y),
    tileLoadFunction: loadTile(track) as never,
    wrapX: false,
    attributions: round.attribution,
  });

  const centerMark = new VectorLayer({
    source: new VectorSource({ features: [new Feature(new Point(center))] }),
    style: STYLE_CENTER,
  });

  const map = new MapBrowser({
    target,
    layers: [new TileLayer({ source }), centerMark],
    controls: defaultControls({ attribution: false, rotate: false }),
    view: new View({
      projection,
      center,
      resolution: 2 ** round.max_zoom,
      maxResolution: 2 ** round.max_zoom,
      minResolution: 0.5,
      extent,
      showFullExtent: true,
      constrainOnlyCenter: false,
    }),
  });

  /*
   * Приближение идёт туда, куда смотрит игрок: колесом и щипком — к курсору,
   * как в любой карте. Раньше вид на каждом шаге зума возвращался к
   * перекрестию, чтобы цель не уезжала за край, но рассматривать при этом
   * можно было только её. А смотреть надо по сторонам: опознают место как раз
   * по окраинам, реке и дорогам, а не по центральному кварталу.
   *
   * Вернуться к цели можно кнопкой на снимке и клавишей R.
   */

  /**
   * Снимок заполняет экран целиком: чёрные поля по бокам выглядели бы
   * недоделкой. Отдалить до полного участка игрок при желании может сам.
   */
  const fitToCover = () => {
    const [width = size, height = size] = map.getSize() ?? [];
    map.getView().setResolution(size / Math.max(width, height, 1));
    map.getView().setCenter(center);
  };

  fitToCover();

  /*
   * Снимок можно повернуть двумя пальцами, и на телефоне это выходит случайно:
   * щипок с лёгким проворотом браузер считает поворотом. Развёрнутый снимок
   * читается хуже — привычка «север наверху» никуда не девается, — поэтому о
   * повороте сообщаем наружу, и игроку показывают кнопку, которая его снимает.
   */
  const view = map.getView();
  const reportRotation = () => {
    onRotated(view.getRotation() !== 0);
  };

  view.on("change:rotation", reportRotation);

  return {
    map,
    reset: fitToCover,
    straighten: () => {
      view.setRotation(0);
    },
    destroy: () => {
      view.un("change:rotation", reportRotation);
      map.setTarget(undefined);
      map.dispose();
    },
  };
}
