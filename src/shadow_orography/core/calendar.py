"""Calendar computation engine."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd
from shapely.geometry import Polygon

from shadow_orography.core.geometry import intersects_fast, shadow_ellipse_polygon
from shadow_orography.core.shadow_model import ProjectParameters, Turbine
from shadow_orography.core.solar import (
    compute_solar_position,
    filter_daylight,
    make_yearly_time_index,
)


def compute_shadow_calendar(
    aoi_polygon: Polygon,
    turbines: list[Turbine],
    parameters: ProjectParameters,
) -> pd.DataFrame:
    """Compute timestamps where each turbine shadow intersects AOI."""
    times = make_yearly_time_index(
        year=parameters.year,
        timezone=parameters.timezone,
        timestep_minutes=parameters.timestep_minutes,
    )
    solar = compute_solar_position(times, parameters.latitude, parameters.longitude)
    solar_daylight = filter_daylight(solar, parameters.min_solar_elevation_deg)

    rows: list[dict[str, object]] = []
    for timestamp, row in solar_daylight.iterrows():
        elevation = float(row["apparent_elevation"])
        azimuth = float(row["azimuth"])
        for turbine in turbines:
            candidate = shadow_ellipse_polygon(
                turbine_x=turbine.x,
                turbine_y=turbine.y,
                hub_height_m=turbine.hub_height_m,
                rotor_radius_m=turbine.rotor_radius_m,
                sun_azimuth_deg=azimuth,
                sun_elevation_deg=elevation,
            )
            if intersects_fast(aoi_polygon, candidate):
                timestamp_local = timestamp.isoformat()
                rows.append(
                    {
                        "turbine_id": turbine.turbine_id,
                        "timestamp_local": timestamp_local,
                        "date": timestamp.strftime("%Y-%m-%d"),
                        "time": timestamp.strftime("%H:%M:%S"),
                        "sun_azimuth_deg": azimuth,
                        "sun_elevation_deg": elevation,
                    }
                )

    return pd.DataFrame(rows)


def export_results_csv(results: pd.DataFrame, output_path: str | Path) -> Path:
    """Export a computed calendar to CSV."""
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(out_path, index=False)
    return out_path


def project_to_dict(
    turbines: list[Turbine],
    aoi_path: str,
    parameters: ProjectParameters,
    results_path: str | None,
) -> dict[str, object]:
    """Build project serialization dictionary."""
    return {
        "turbines": [asdict(turbine) for turbine in turbines],
        "aoi_path": aoi_path,
        "parameters": asdict(parameters),
        "results_path": results_path,
    }
