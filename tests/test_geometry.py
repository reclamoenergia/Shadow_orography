import pytest

from shadow_orography.core.geometry import shadow_ellipse_polygon


def test_ellipse_area_positive() -> None:
    ellipse = shadow_ellipse_polygon(
        turbine_x=0,
        turbine_y=0,
        hub_height_m=100,
        rotor_radius_m=60,
        sun_azimuth_deg=180,
        sun_elevation_deg=20,
    )
    assert ellipse.area > 0


def test_ellipse_rotation_changes_bbox() -> None:
    ellipse_a = shadow_ellipse_polygon(0, 0, 100, 50, 90, 25)
    ellipse_b = shadow_ellipse_polygon(0, 0, 100, 50, 180, 25)

    width_a = ellipse_a.bounds[2] - ellipse_a.bounds[0]
    height_a = ellipse_a.bounds[3] - ellipse_a.bounds[1]
    width_b = ellipse_b.bounds[2] - ellipse_b.bounds[0]
    height_b = ellipse_b.bounds[3] - ellipse_b.bounds[1]

    assert pytest.approx(width_a, rel=1e-3) != width_b
    assert pytest.approx(height_a, rel=1e-3) != height_b
