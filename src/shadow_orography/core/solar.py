"""Solar position utilities."""

from __future__ import annotations

import warnings
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import pvlib


def make_yearly_time_index(
    year: int,
    timezone: str = "Europe/Rome",
    timestep_minutes: int = 15,
) -> pd.DatetimeIndex:
    """Build a timezone-aware time index covering a full year."""
    try:
        tzinfo = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        warnings.warn(
            (
                f"Timezone '{timezone}' not found on this system. "
                "Falling back to UTC so the application can continue."
            ),
            RuntimeWarning,
            stacklevel=2,
        )
        tzinfo = ZoneInfo("UTC")

    start = pd.Timestamp(year=year, month=1, day=1, tz=tzinfo)
    end = pd.Timestamp(year=year + 1, month=1, day=1, tz=tzinfo)
    return pd.date_range(
        start=start,
        end=end,
        inclusive="left",
        freq=f"{timestep_minutes}min",
    )


def compute_solar_position(
    times: pd.DatetimeIndex,
    latitude: float,
    longitude: float,
) -> pd.DataFrame:
    """Compute solar azimuth and apparent elevation for timestamps."""
    return pvlib.solarposition.get_solarposition(times, latitude, longitude)


def filter_daylight(
    solar_position: pd.DataFrame,
    min_solar_elevation_deg: float,
) -> pd.DataFrame:
    """Filter rows to only timestamps above a minimum apparent elevation."""
    return solar_position.loc[
        solar_position["apparent_elevation"] > min_solar_elevation_deg
    ].copy()
