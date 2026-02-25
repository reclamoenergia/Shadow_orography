from shapely.geometry import Polygon

from shadow_orography.core.calendar import compute_shadow_calendar
from shadow_orography.core.shadow_model import ProjectParameters, Turbine


def test_known_case_has_intersection() -> None:
    aoi = Polygon([(-200, -200), (200, -200), (200, 200), (-200, 200)])
    turbines = [
        Turbine(
            turbine_id="T-1",
            x=0.0,
            y=0.0,
            hub_height_m=100.0,
            rotor_diameter_m=120.0,
        )
    ]
    params = ProjectParameters(
        latitude=45.0,
        longitude=10.0,
        year=2024,
        min_solar_elevation_deg=5.0,
        timestep_minutes=15,
    )

    results = compute_shadow_calendar(aoi, turbines, params)
    assert not results.empty
    assert (results["turbine_id"] == "T-1").any()
