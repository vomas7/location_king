/** Подложка обычной карты. Общая для карты догадки и карты результата. */

import Attribution from "ol/control/Attribution";
import { defaults as defaultControls } from "ol/control/defaults";
import type Control from "ol/control/Control";
import type Collection from "ol/Collection";
import TileLayer from "ol/layer/Tile";
import OSM from "ol/source/OSM";

/**
 * Указание правообладателя обязательно по лицензии ODbL, поэтому оно не
 * прячется под кнопку: собственный контрол OpenLayers на маленькой карте
 * схлопывается сам, а спрятанная подпись — это подпись, которой нет.
 */
const ATTRIBUTION =
  '© участники <a href="https://www.openstreetmap.org/copyright" ' +
  'target="_blank" rel="noreferrer noopener">OpenStreetMap</a>';

export function osmLayer(): TileLayer<OSM> {
  return new TileLayer({ source: new OSM({ attributions: ATTRIBUTION }) });
}

/** Набор контролов карты с всегда видимой подписью об источнике данных. */
export function osmControls(): Collection<Control> {
  return defaultControls({ attribution: false, rotate: false }).extend([
    new Attribution({ collapsible: false }),
  ]);
}
