"""Geometry and GIS helpers."""

from __future__ import annotations

import math
from pathlib import Path

import shapefile
from pyproj import CRS
from shapely import affinity
from shapely.geometry import MultiPolygon, Polygon, shape


def load_polygon_from_shapefile(path: str | Path) -> tuple[Polygon, CRS | None]:
    """Load the first polygon from a shapefile and optional CRS from PRJ."""
    shp_path = Path(path)
    reader = shapefile.Reader(str(shp_path))
    record = reader.shapeRecords()[0]
    geom = shape(record.shape.__geo_interface__)
    if isinstance(geom, MultiPolygon):
        polygon = max(geom.geoms, key=lambda g: g.area)
    elif isinstance(geom, Polygon):
        polygon = geom
    else:
        raise ValueError("Expected polygon geometry in shapefile")

    prj_path = shp_path.with_suffix(".prj")
    crs = None
    if prj_path.exists():
        crs = CRS.from_wkt(prj_path.read_text(encoding="utf-8"))
    return polygon, crs


def shadow_ellipse_polygon(
    turbine_x: float,
    turbine_y: float,
    hub_height_m: float,
    rotor_radius_m: float,
    sun_azimuth_deg: float,
    sun_elevation_deg: float,
    num_points: int = 64,
) -> Polygon:
    """Build worst-case rotor shadow ellipse polygon for flat terrain."""
    elevation_rad = math.radians(max(sun_elevation_deg, 0.001))
    azimuth_rad = math.radians(sun_azimuth_deg)

    d = hub_height_m / math.tan(elevation_rad)
    a = rotor_radius_m / math.sin(elevation_rad)
    b = rotor_radius_m

    dx = -d * math.sin(azimuth_rad)
    dy = -d * math.cos(azimuth_rad)

    center_x = turbine_x + dx
    center_y = turbine_y + dy

    ellipse = Point(center_x, center_y).buffer(1.0, resolution=max(16, num_points // 4))
    ellipse = affinity.scale(ellipse, xfact=a, yfact=b, origin=(center_x, center_y))
    rotation_deg = 90.0 - sun_azimuth_deg
    ellipse = affinity.rotate(ellipse, rotation_deg, origin=(center_x, center_y))
    return Polygon(ellipse.exterior.coords)


def intersects_fast(aoi_polygon: Polygon, candidate: Polygon) -> bool:
    """Intersection check with bounds pre-check."""
    minx1, miny1, maxx1, maxy1 = aoi_polygon.bounds
    minx2, miny2, maxx2, maxy2 = candidate.bounds
    if maxx1 < minx2 or maxx2 < minx1 or maxy1 < miny2 or maxy2 < miny1:
        return False
    return aoi_polygon.intersects(candidate)


# Local import needed only for type construction above.
from shapely.geometry import Point  # noqa: E402
