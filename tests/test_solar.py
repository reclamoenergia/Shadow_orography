from shadow_orography.core.solar import compute_solar_position, make_yearly_time_index


def test_solar_ranges() -> None:
    times = make_yearly_time_index(2024, "Europe/Rome", 15)[:96]
    solar = compute_solar_position(times, latitude=45.0, longitude=10.0)

    assert (solar["apparent_elevation"] > -90).all()
    assert (solar["apparent_elevation"] < 90).all()
    assert (solar["azimuth"] >= 0).all()
    assert (solar["azimuth"] <= 360).all()


def test_make_yearly_time_index_falls_back_to_utc_for_unknown_timezone() -> None:
    times = make_yearly_time_index(2024, "Invalid/Timezone", 60)

    assert str(times.tz) == "UTC"
    assert len(times) == 366 * 24
