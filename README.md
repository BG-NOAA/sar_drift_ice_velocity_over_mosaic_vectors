# SAR Drift Ice Velocity over MOSAiC Vectors

Processes SAR-derived sea-ice drift files into filtered CSVs and styled GeoPackages for QGIS visualization and comparison with MOSAiC buoy observations.

**Organization:** NOAA STAR SOCD / Colorado State University CIRA  
**Author:** Brendon Gory (brendon.gory@noaa.gov)  
**Supervisor:** Dr. Prasanjit Dash (prasanjit.dash@noaa.gov)

---

## Overview

This tool reads a directory of SAR drift delimited files (one per buoy), applies a chain of quality filters, reprojects coordinates from EPSG:4326 to EPSG:3413 (NSIDC Sea Ice Polar Stereographic North), computes kinematic drift quantities, and writes per-buoy outputs:

- **CSV** — filtered, reduced-column tabular file
- **GeoPackage** — drift-line vectors in EPSG:3413 with an embedded QML style for automatic rendering in QGIS

---

## Repository Structure

```
.
├── sar_drift_ice_velocity_over_mosaic_vectors.py   # Main entry point
├── util.py                                          # Shared utilities and I/O
├── constants.py                                     # Versioned algorithm parameters
├── config.json                                      # Runtime configuration (user-supplied)
├── meta/
│   └── graduated_quivers.qml                        # QGIS style file embedded in GeoPackages
├── environment.yml                                  # Conda environment
└── requirements.txt                                 # pip dependencies
```

---

## Installation

### Conda (recommended on Windows)

PROJ and GDAL native libraries are bundled by conda-forge, which avoids manual DLL setup.

```bash
conda env create -f environment.yml
conda activate sar_mosaic_vectors
```

### pip (Linux / macOS)

Install system libraries first, then pip packages:

```bash
# Debian/Ubuntu
sudo apt install libproj-dev libgdal-dev

# macOS (Homebrew)
brew install proj gdal

pip install -r requirements.txt
```

---

## Configuration

Copy and edit `config.json` before running. All keys are required.

| Key | Type | Description |
|---|---|---|
| `sar_drift_directory` | `str` | Path to directory containing SAR drift `.txt` / `.csv` files |
| `qml_file` | `str` | Path to the QGIS QML style file to embed in each GeoPackage |
| `clear_output_dir` | `bool` | If `true`, delete and recreate `csv/`, `gpkg/`, and `log/` before running |
| `delimiter` | `str` | Field separator in input files (e.g. `","`, `"\t"`) |
| `skip_rows_before_header` | `int` | Number of rows to skip before the header row |
| `verbose` | `bool` | Print resolved configuration parameters to the console |
| `version` | `str` | Output file version string (e.g. `"01"`) appended to output filenames |

**Example `config.json`:**

```json
{
  "sar_drift_directory": "mosaic",
  "qml_file": "meta/graduated_quivers.qml",
  "clear_output_dir": true,
  "delimiter": ",",
  "skip_rows_before_header": 0,
  "verbose": true,
  "version": "01"
}
```

---

## Usage

```bash
python sar_drift_ice_velocity_over_mosaic_vectors.py -c config.json
```

The `-c` / `--config_file` argument is required.

---

## Outputs

All outputs are written relative to the working directory.

| Directory | Contents |
|---|---|
| `csv/` | `NOAA_SIVelocity_SAR_<buoy_id>_v<version>.csv` — filtered tabular data |
| `gpkg/` | `NOAA_SIVelocity_SAR_<buoy_id>_v<version>.gpkg` — drift-line GeoPackage |
| `log/` | `run_<YYYYMMDD_HHMMSS>.log` — timestamped run log |

### Output columns (CSV / GeoPackage attribute table)

| Column | Units | Description |
|---|---|---|
| `latitude_1`, `longitude_1` | degrees | Start position |
| `latitude_2`, `longitude_2` | degrees | End position |
| `X1`, `Y1`, `X2`, `Y2` | m (EPSG:3413) | Projected start / end coordinates |
| `date_start`, `date_end` | UTC datetime | Observation window |
| `duration_s` | s | Observation duration |
| `sea_ice_x_displacement` | m | X displacement (EPSG:3413) |
| `sea_ice_y_displacement` | m | Y displacement (EPSG:3413) |
| `u_ms`, `v_ms` | m s⁻¹ | Cartesian velocity components (EPSG:3413) |
| `sea_ice_speed` | m s⁻¹ | Geodesic drift speed |
| `sea_ice_speed_kmdy` | km day⁻¹ | Drift speed, scaled to daily rate |
| `direction_of_sea_ice_displacement` | degrees | Forward azimuth (WGS84 geodesic) |
| `distance` | m | Geodesic displacement distance |
| `sensor1`, `sensor2` | — | SAR platform identifiers parsed from filenames |
| `scene_id` | — | `File1_File2` scene-pair identifier |
| `Maxcorr1`, `Maxcorr2` | — | Maximum correlation scores from SAR tracking |

---

## Quality Filters

The following filters are applied in order to each buoy file. Rows failing any filter are dropped, and the row counts before and after are logged.

1. **Bearing / speed validity** — removes rows where `direction_of_sea_ice_displacement == 0` or `sea_ice_speed <= 0`
2. **Speed ceiling** — removes rows where `sea_ice_speed >= 25.0 m s⁻¹`
3. **Correlation quality** — removes rows where `Maxcorr2 <= Maxcorr1`

---

## Algorithm Parameters

Rounding precision constants are defined in `constants.py` and version-controlled independently of the configuration file.

| Constant | Default | Applied to |
|---|---|---|
| `BEARING_PRECISION` | `0` | `direction_of_sea_ice_displacement` |
| `SPEED_PRECISION` | `3` | Speed, displacement, and distance fields |
| `DISPLACEMENT_PRECISION` | `4` | `U`, `V`, `dx`, `dy` components |
| `COORDINATE_PRECISION` | `4` | Projected and geographic coordinate columns |

---

## Coordinate Reference Systems

| EPSG | Name | Usage |
|---|---|---|
| 4326 | WGS84 Geographic | Input lat/lon |
| 3413 | NSIDC Sea Ice Polar Stereographic North | Projected coordinates and GeoPackage geometry |
| 3408 | NSIDC EASE-Grid North | Available transformer (not used in primary output) |
| 3411 | Hughes 1980 Polar Stereographic | Available transformer (not used in primary output) |

Geodesic bearing and distance are computed on the WGS84 ellipsoid using `pyproj.Geod`.

---

## Logging

A timestamped log file is written to `log/run_<YYYYMMDD_HHMMSS>.log` for each run. Log entries cover run start/end times, input file discovery, per-file initial row counts, and rows dropped at each filter stage.

Logger name: `sar_drift_ice_velocity_over_maosaic_vectors`

---

## License

Copyright © 2025 NOAA STAR SOCD and Colorado State University CIRA  
Version 1.0.0 — POC: Brendon Gory (brendon.gory@noaa.gov)

Distributed under the MIT License. See source file headers for full license text.
