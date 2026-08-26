"""Тесты тайловой арифметики и расстояний."""

import math

import pytest

from app.utils.geo import (
    EQUATOR_KM,
    haversine_km,
    lonlat_to_tile,
    tile_bounds,
    tile_center,
    tile_width_km,
    zoom_for_extent,
)


def test_haversine_zero_for_same_point():
    assert haversine_km(37.6, 55.75, 37.6, 55.75) == 0.0


def test_haversine_known_distance():
    """Москва — Санкт-Петербург, около 635 км по прямой."""
    distance = haversine_km(37.6173, 55.7558, 30.3351, 59.9391)
    assert 630 < distance < 640


def test_haversine_is_symmetric():
    forward = haversine_km(10.0, 20.0, -30.0, 45.0)
    backward = haversine_km(-30.0, 45.0, 10.0, 20.0)
    assert forward == pytest.approx(backward)


@pytest.mark.parametrize(
    ("lon", "lat", "zoom"),
    [(37.6, 55.75, 12), (-122.4, 37.8, 15), (0.0, 0.0, 3), (139.7, 35.7, 17)],
)
def test_point_lies_inside_its_own_tile(lon: float, lat: float, zoom: int):
    x, y = lonlat_to_tile(lon, lat, zoom)
    west, south, east, north = tile_bounds(x, y, zoom)

    assert west <= lon <= east
    assert south <= lat <= north


def test_tile_center_maps_back_to_same_tile():
    x, y = lonlat_to_tile(37.6, 55.75, 14)
    center_lon, center_lat = tile_center(x, y, 14)

    assert lonlat_to_tile(center_lon, center_lat, 14) == (x, y)


def test_zoom_zero_is_the_whole_world():
    assert tile_bounds(0, 0, 0) == pytest.approx((-180.0, -85.0511287, 180.0, 85.0511287), abs=1e-5)


def test_tile_width_halves_with_each_zoom_level():
    wide = tile_width_km(*lonlat_to_tile(37.6, 55.75, 10), 10)
    narrow = tile_width_km(*lonlat_to_tile(37.6, 55.75, 11), 11)

    assert narrow == pytest.approx(wide / 2, rel=0.01)


def test_tile_width_at_equator_matches_equator_length():
    assert tile_width_km(0, 0, 0) == pytest.approx(EQUATOR_KM, rel=0.001)


@pytest.mark.parametrize("extent_km", [1.0, 5.0, 25.0, 100.0])
def test_zoom_for_extent_gives_tile_of_requested_size(extent_km: float):
    lat = 55.75
    zoom = zoom_for_extent(lat, extent_km)
    width = tile_width_km(*lonlat_to_tile(37.6, lat, zoom), zoom)

    # Зум дискретный, поэтому попадание в пределах множителя 2 — это лучшее возможное
    assert 0.5 <= width / extent_km <= 2.0


def test_zoom_for_extent_respects_limits():
    assert zoom_for_extent(0.0, 0.001, min_zoom=3, max_zoom=17) == 17
    assert zoom_for_extent(0.0, 1_000_000.0, min_zoom=3, max_zoom=17) == 3


def test_extreme_latitudes_are_clamped_to_mercator_range():
    x, y = lonlat_to_tile(0.0, 89.9, 5)
    assert 0 <= y < 2**5
    assert not math.isnan(tile_center(x, y, 5)[1])
