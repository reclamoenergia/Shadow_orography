from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np

from wtg_shadow_hours.core import Turbine, accumulate_shadow_hours, solar_position_noaa


def test_accumulation_adds_overlap_once_per_timestep():
    x = np.array([-10.0, 0.0, 10.0])
    y = np.array([10.0, 0.0, -10.0])
    turbines = [
        Turbine(0.0, 0.0, rotor_diam_m=20.0, hub_height_m=50.0, turbine_id="A"),
        Turbine(1.0, 0.0, rotor_diam_m=20.0, hub_height_m=50.0, turbine_id="B"),
    ]
    az = np.array([180.0])
    el = np.array([45.0])
    out = accumulate_shadow_hours(x, y, turbines, az, el, timestep_hours=0.25, min_solar_elevation_deg=0.0)
    assert np.max(out) <= 0.25


def test_solar_position_ranges():
    times = [datetime(2025, 6, 21, 12, 0, tzinfo=ZoneInfo("Europe/Rome"))]
    az, el = solar_position_noaa(times, latitude_deg=45.0, longitude_deg=10.0)
    assert 0.0 <= az[0] <= 360.0
    assert -90.0 <= el[0] <= 90.0
