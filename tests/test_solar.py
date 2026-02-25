from shadow_orography.core.solar import compute_solar_position, make_yearly_time_index


def test_solar_ranges() -> None:
    times = make_yearly_time_index(2024, "Europe/Rome", 15)[:96]
    solar = compute_solar_position(times, latitude=45.0, longitude=10.0)

    assert (solar["apparent_elevation"] > -90).all()
    assert (solar["apparent_elevation"] < 90).all()
    assert (solar["azimuth"] >= 0).all()
    assert (solar["azimuth"] <= 360).all()
