/**
 * Карты игры на OpenLayers.
 *
 * Спутниковая карта раунда живёт в пиксельной проекции: у неё нет ни широты,
 * ни долготы — только локальная сетка тайлов, которую переводит сервер. Карта
 * догадки и карта результата — обычные, в EPSG:3857.
 */

import { authHeaders, tileUrl } from "./api.js";

const TILE_SIZE = 256;
const TILE_STATE_ERROR = 3;

const COLOR_GUESS = "#38bdf8";
const COLOR_TARGET = "#fbbf24";

// ── Стили точек ──────────────────────────────────────────────────────

function pointStyle(color) {
    return new ol.style.Style({
        image: new ol.style.Circle({
            radius: 8,
            fill: new ol.style.Fill({ color }),
            stroke: new ol.style.Stroke({ color: "#0a0e14", width: 3 }),
        }),
    });
}

const STYLE_GUESS = pointStyle(COLOR_GUESS);
const STYLE_TARGET = pointStyle(COLOR_TARGET);

/**
 * Перекрестие в центре показанной области.
 *
 * Очки считаются от этой точки, поэтому игрок должен видеть, куда именно
 * целиться. Тёмная подложка нужна, чтобы метка читалась и на снегу, и на
 * тёмной воде.
 */
const STYLE_CENTER = [
    new ol.style.Style({
        image: new ol.style.RegularShape({
            points: 4,
            radius: 16,
            radius2: 0,
            stroke: new ol.style.Stroke({ color: "rgba(0, 0, 0, 0.55)", width: 5 }),
        }),
    }),
    new ol.style.Style({
        image: new ol.style.RegularShape({
            points: 4,
            radius: 16,
            radius2: 0,
            stroke: new ol.style.Stroke({ color: "rgba(255, 255, 255, 0.95)", width: 2 }),
        }),
    }),
    new ol.style.Style({
        image: new ol.style.Circle({
            radius: 5,
            stroke: new ol.style.Stroke({ color: "rgba(255, 255, 255, 0.95)", width: 2 }),
        }),
    }),
];

const STYLE_LINE = new ol.style.Style({
    stroke: new ol.style.Stroke({ color: "#e2e8f0", width: 2, lineDash: [6, 6] }),
});

function baseLayer() {
    return new ol.layer.Tile({
        source: new ol.source.OSM({
            attributions: "© OpenStreetMap",
        }),
    });
}

function pointFeature(lonLat) {
    return new ol.Feature(new ol.geom.Point(ol.proj.fromLonLat(lonLat)));
}

// ── Спутниковая карта раунда ─────────────────────────────────────────

/**
 * Загрузка тайла с заголовком авторизации.
 *
 * Обычный <img src> заголовки не отправляет, поэтому тайл забирается
 * через fetch и подставляется как blob.
 */
async function loadTile(tile, src) {
    try {
        const response = await fetch(src, { headers: authHeaders() });
        if (!response.ok) {
            tile.setState(TILE_STATE_ERROR);
            return;
        }

        const url = URL.createObjectURL(await response.blob());
        const image = tile.getImage();
        image.onload = () => URL.revokeObjectURL(url);
        image.onerror = () => {
            URL.revokeObjectURL(url);
            tile.setState(TILE_STATE_ERROR);
        };
        image.src = url;
    } catch {
        tile.setState(TILE_STATE_ERROR);
    }
}

/** Создать карту снимка для раунда. Возвращает объект с методом destroy. */
export function createSatelliteMap(target, round) {
    const maxZoom = round.max_zoom;
    const size = TILE_SIZE * 2 ** maxZoom;
    const extent = [0, -size, size, 0];

    const projection = new ol.proj.Projection({
        code: `round:${round.id}`,
        units: "pixels",
        extent,
    });

    const resolutions = Array.from({ length: maxZoom + 1 }, (_, z) => 2 ** (maxZoom - z));

    const source = new ol.source.XYZ({
        projection,
        tileGrid: new ol.tilegrid.TileGrid({
            extent,
            origin: [0, 0],
            resolutions,
            tileSize: TILE_SIZE,
        }),
        tileUrlFunction: ([z, x, y]) => tileUrl(round.tiles_url, z, x, y),
        tileLoadFunction: loadTile,
        wrapX: false,
        attributions: round.attribution,
    });

    // Отметка центра области: именно её игрок и должен найти на карте
    const centerMark = new ol.layer.Vector({
        source: new ol.source.Vector({
            features: [new ol.Feature(new ol.geom.Point([size / 2, -size / 2]))],
        }),
        style: STYLE_CENTER,
    });

    const map = new ol.Map({
        target,
        layers: [new ol.layer.Tile({ source }), centerMark],
        controls: ol.control.defaults.defaults({ attribution: false, rotate: false }),
        view: new ol.View({
            projection,
            center: [size / 2, -size / 2],
            resolution: 2 ** maxZoom,
            maxResolution: 2 ** maxZoom,
            minResolution: 0.5,
            extent,
            showFullExtent: true,
            constrainOnlyCenter: false,
        }),
    });

    // Снимок заполняет экран целиком: чёрные поля по бокам выглядели бы
    // недоделкой. Отдалить до полной области игрок при желании может сам.
    const [width, height] = map.getSize() ?? [size, size];
    map.getView().setResolution(size / Math.max(width, height, 1));

    return {
        map,
        destroy() {
            map.setTarget(undefined);
            map.dispose();
        },
    };
}

// ── Карта догадки ────────────────────────────────────────────────────

/** Карта мира, на которой игрок ставит точку. */
export function createGuessMap(target, onPick) {
    const source = new ol.source.Vector();

    const map = new ol.Map({
        target,
        layers: [baseLayer(), new ol.layer.Vector({ source, style: STYLE_GUESS })],
        controls: ol.control.defaults.defaults({ attribution: false, rotate: false }),
        view: new ol.View({
            center: ol.proj.fromLonLat([20, 30]),
            zoom: 1,
            minZoom: 1,
            maxZoom: 18,
        }),
    });

    map.on("click", (event) => {
        const [longitude, latitude] = ol.proj.toLonLat(event.coordinate);

        source.clear();
        source.addFeature(pointFeature([longitude, latitude]));
        onPick({ longitude, latitude });
    });

    return {
        map,
        clear: () => source.clear(),
        refresh: () => map.updateSize(),
    };
}

// ── Карта результата ─────────────────────────────────────────────────

/** Карта с целью, догадкой и линией между ними. */
export function createResultMap(target) {
    const source = new ol.source.Vector();

    const map = new ol.Map({
        target,
        layers: [
            baseLayer(),
            new ol.layer.Vector({
                source,
                style: (feature) => {
                    if (feature.get("kind") === "line") return STYLE_LINE;
                    return feature.get("kind") === "target" ? STYLE_TARGET : STYLE_GUESS;
                },
            }),
        ],
        controls: ol.control.defaults.defaults({ attribution: false, rotate: false }),
        interactions: ol.interaction.defaults.defaults({ mouseWheelZoom: false }),
        view: new ol.View({ center: [0, 0], zoom: 1 }),
    });

    return {
        map,

        show(targetLonLat, guessLonLat) {
            source.clear();

            const targetFeature = pointFeature(targetLonLat);
            targetFeature.set("kind", "target");
            source.addFeature(targetFeature);

            if (guessLonLat) {
                const guessFeature = pointFeature(guessLonLat);
                guessFeature.set("kind", "guess");

                const line = new ol.Feature(
                    new ol.geom.LineString([
                        ol.proj.fromLonLat(guessLonLat),
                        ol.proj.fromLonLat(targetLonLat),
                    ]),
                );
                line.set("kind", "line");

                source.addFeatures([guessFeature, line]);
            }

            map.updateSize();
            map.getView().fit(source.getExtent(), {
                size: map.getSize(),
                padding: [60, 60, 60, 60],
                maxZoom: 12,
                duration: 400,
            });
        },
    };
}
