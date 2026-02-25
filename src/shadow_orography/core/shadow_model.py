"""Domain models for shadow computations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Turbine:
    """Wind turbine definition in planar map coordinates."""

    turbine_id: str
    x: float
    y: float
    hub_height_m: float
    rotor_diameter_m: float

    @property
    def rotor_radius_m(self) -> float:
        """Return rotor radius in meters."""
        return self.rotor_diameter_m / 2.0


@dataclass(frozen=True)
class ProjectParameters:
    """Project-level parameters used for calendar generation."""

    latitude: float
    longitude: float
    year: int
    min_solar_elevation_deg: float
    timezone: str = "Europe/Rome"
    timestep_minutes: int = 15
