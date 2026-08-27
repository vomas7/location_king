/** Подложка обычной карты. Общая для карты догадки и карты результата. */

import TileLayer from "ol/layer/Tile";
import OSM from "ol/source/OSM";

export function osmLayer(): TileLayer<OSM> {
  return new TileLayer({ source: new OSM({ attributions: "© OpenStreetMap" }) });
}
