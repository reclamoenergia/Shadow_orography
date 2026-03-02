"""Core math utilities reusable outside QGIS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import pi
from zoneinfo import ZoneInfo

import numpy as np


@dataclass(frozen=True)
class Turbine:
    x: float
    y: float
    rotor_diam_m: float
    hub_height_m: float
    turbine_id: str


def generate_yearly_timestamps(year: int, timestep_minutes: int, timezone: str = "Europe/Rome"):
    tz = ZoneInfo(timezone)
    start = datetime(year, 1, 1, 0, 0, tzinfo=tz)
    end = datetime(year + 1, 1, 1, 0, 0, tzinfo=tz)
    step = timedelta(minutes=timestep_minutes)
    out = []
    cur = start
    while cur < end:
        out.append(cur)
        cur += step
    return out


def solar_position_noaa(times, latitude_deg: float, longitude_deg: float):
    """Approximate solar position using NOAA equations."""
    lat_rad = np.deg2rad(latitude_deg)

    day_of_year = np.array([t.timetuple().tm_yday for t in times], dtype=float)
    hour = np.array([t.hour + t.minute / 60 + t.second / 3600 for t in times], dtype=float)
    tz_offset_hours = np.array([t.utcoffset().total_seconds() / 3600 for t in times], dtype=float)

    gamma = 2.0 * pi / 365.0 * (day_of_year - 1.0 + (hour - 12.0) / 24.0)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * np.cos(gamma)
        - 0.032077 * np.sin(gamma)
        - 0.014615 * np.cos(2.0 * gamma)
        - 0.040849 * np.sin(2.0 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * np.cos(gamma)
        + 0.070257 * np.sin(gamma)
        - 0.006758 * np.cos(2.0 * gamma)
        + 0.000907 * np.sin(2.0 * gamma)
        - 0.002697 * np.cos(3.0 * gamma)
        + 0.00148 * np.sin(3.0 * gamma)
    )

    true_solar_time_min = hour * 60.0 + eqtime + 4.0 * longitude_deg - 60.0 * tz_offset_hours
    hour_angle_rad = np.deg2rad((true_solar_time_min / 4.0) - 180.0)

    cos_zenith = np.sin(lat_rad) * np.sin(decl) + np.cos(lat_rad) * np.cos(decl) * np.cos(hour_angle_rad)
    cos_zenith = np.clip(cos_zenith, -1.0, 1.0)
    zenith = np.arccos(cos_zenith)
    elevation_deg = 90.0 - np.rad2deg(zenith)

    azimuth_rad = np.arctan2(
        np.sin(hour_angle_rad),
        np.cos(hour_angle_rad) * np.sin(lat_rad) - np.tan(decl) * np.cos(lat_rad),
    )
    azimuth_deg = (np.rad2deg(azimuth_rad) + 180.0) % 360.0
    return azimuth_deg, elevation_deg


def accumulate_shadow_hours(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    turbines: list[Turbine],
    azimuth_deg: np.ndarray,
    elevation_deg: np.ndarray,
    timestep_hours: float,
    min_solar_elevation_deg: float,
):
    xx, yy = np.meshgrid(x_coords, y_coords)
    out = np.zeros_like(xx, dtype=np.float32)

    valid = elevation_deg > max(0.0, float(min_solar_elevation_deg))
    for az, el in zip(azimuth_deg[valid], elevation_deg[valid]):
        el_rad = np.deg2rad(el)
        sin_el = np.sin(el_rad)
        tan_el = np.tan(el_rad)
        step_mask = np.zeros_like(out, dtype=bool)

        for turbine in turbines:
            radius = turbine.rotor_diam_m * 0.5
            d = turbine.hub_height_m / tan_el
            a = radius / sin_el
            b = radius
            az_rad = np.deg2rad(az)

            center_x = turbine.x - d * np.sin(az_rad)
            center_y = turbine.y - d * np.cos(az_rad)
            theta = np.deg2rad(90.0 - az)

            cos_t = np.cos(theta)
            sin_t = np.sin(theta)
            x_extent = abs(a * cos_t) + abs(b * sin_t)
            y_extent = abs(a * sin_t) + abs(b * cos_t)

            x_min = center_x - x_extent
            x_max = center_x + x_extent
            y_min = center_y - y_extent
            y_max = center_y + y_extent

            cols = np.where((x_coords >= x_min) & (x_coords <= x_max))[0]
            rows = np.where((y_coords >= y_min) & (y_coords <= y_max))[0]
            if cols.size == 0 or rows.size == 0:
                continue

            sub_x = xx[np.ix_(rows, cols)] - center_x
            sub_y = yy[np.ix_(rows, cols)] - center_y

            xr = sub_x * cos_t + sub_y * sin_t
            yr = -sub_x * sin_t + sub_y * cos_t
            in_ellipse = (xr / a) ** 2 + (yr / b) ** 2 <= 1.0
            step_mask[np.ix_(rows, cols)] |= in_ellipse

        out[step_mask] += timestep_hours

    return out
