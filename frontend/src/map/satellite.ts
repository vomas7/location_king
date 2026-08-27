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

import { tileUrl } from "~/api/client";
import { authHeaders } from "~/api/tokens";
import type { RoundView } from "~/api/types";
import { STYLE_CENTER } from "~/map/styles";

const TILE_SIZE = 256;

export interface SatelliteMap {
  readonly map: OlMap;
  /** Вернуть вид к исходному масштабу, показывающему участок целиком. */
  reset: () => void;
  destroy: () => void;
}

/**
 * Загрузка тайла с заголовком авторизации.
 *
 * Обычный <img src> заголовки не отправляет, поэтому тайл забирается через
 * fetch и подставляется как blob.
 */
function loadTile(onError: () => void) {
  return (tile: ImageTile, src: string): void => {
    void (async () => {
      try {
        const response = await fetch(src, { headers: authHeaders() });
        if (!response.ok) {
          tile.setState(TileState.ERROR);
          onError();
          return;
        }

        const objectUrl = URL.createObjectURL(await response.blob());
        const image = tile.getImage() as HTMLImageElement;

        image.onload = () => {
          URL.revokeObjectURL(objectUrl);
        };
        image.onerror = () => {
          URL.revokeObjectURL(objectUrl);
          tile.setState(TileState.ERROR);
          onError();
        };
        image.src = objectUrl;
      } catch {
        tile.setState(TileState.ERROR);
        onError();
      }
    })();
  };
}

export function createSatelliteMap(
  target: HTMLElement,
  round: RoundView,
  onTileError: () => void,
): SatelliteMap {
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
    tileLoadFunction: loadTile(onTileError) as never,
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

  return {
    map,
    reset: fitToCover,
    destroy: () => {
      map.setTarget(undefined);
      map.dispose();
    },
  };
}
