# WTG Shadow Hours (QGIS Plugin)

WTG Shadow Hours is a QGIS Processing plugin that computes **annual cumulative shadow hours** on a flat surface from multiple wind turbines.

## Model assumptions

- Flat terrain only.
- Worst-case rotor orientation: rotor disk always orthogonal to sun rays.
- Turbine always operating.
- Turbine overlap in the same timestep is counted once (boolean OR per timestep).
- Solar position is computed with an internal NOAA-style approximation (pure Python + NumPy), so no pvlib installation is required.
- Timezone is fixed to `Europe/Rome`.

## Plugin layout

```text
wtg_shadow_hours/
  __init__.py
  metadata.txt
  plugin.py
  processing_provider.py
  core.py
  algorithms/shadow_hours.py
tests/
README.md
```

## Install in QGIS (ZIP)

1. Zip the repository root so that `wtg_shadow_hours/` is at the top level of the ZIP.
2. In QGIS: **Plugins → Manage and Install Plugins… → Install from ZIP**.
3. Select the ZIP and install.
4. Ensure Processing is enabled; the algorithm appears under **Processing Toolbox → WTG Shadow**.

## Required input layer

- Input: a loaded **point vector layer** (shapefile, geopackage, etc.).
- CRS must be a **projected metric CRS** (meters). Geographic CRS (degrees) is rejected.
- Required numeric fields per turbine:
  - `rotor_diam_m`
  - `hub_height_m`
- Optional string field:
  - `turbine_id` (if missing, feature id is used).

## Processing algorithm

- **Name**: `Compute WTG annual shadow hours`
- **Group**: `WTG Shadow`

Parameters:

- Input turbine point layer
- Rotor diameter field (`rotor_diam_m`)
- Hub height field (`hub_height_m`)
- `min_solar_elevation_deg` (default 0)
- `year` (default 2025)
- `timestep_minutes` (allowed: 5, 10, 15, 30; default 15)
- `cellsize_m` (allowed: 10, 20, 25, 50; default 20)
- `buffer_m` (default 2000)
- Output raster destination (GeoTIFF)

## Output

- A raster (`.tif`) with annual shadow hours per cell.
- Added automatically to the map.
- Styled as singleband pseudocolor with layer name: **Annual shadow hours**.

## Lightweight tests

Run outside QGIS:

```bash
pytest -q
```
