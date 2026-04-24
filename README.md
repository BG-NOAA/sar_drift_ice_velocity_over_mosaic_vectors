# SAR Drift Converter & Outlier Tools

This repository converts **SAR sea‑ice drift "gfilter" text outputs** into GIS- and analysis-ready products:

- **Formatted CSV** (cleaned/consistent columns)
- **GeoPackage (`.gpkg`)** with drift lines in a configurable projected CRS — one file per day across all scenes
- **NetCDF (`.nc`)** on a regular grid with metadata populated from a **CDL template** — two files per day: a multi-layered scenes file and a single-layer daily summary
- **Interactive vector HTML** — one file per day across all scenes (levels `00` and `03`)
- Optional utilities: outlier detection (z-score and Mahalanobis)

---

## Requirements

Two dependency files are provided. Use whichever matches your workflow:

**`environment.yml`** (conda, recommended):

```bash
conda env create -f environment.yml
conda activate sar_drift_converter
```

**`requirements.txt`** (pip):

```bash
pip install -r requirements.txt
```

### Package list

| Package | Notes |
|---------|-------|
| `cartopy` | Cartopy basemap rendering in the layer viewer notebook |
| `geopandas` | GeoPackage output |
| `matplotlib` | Quiver plot rendering in the layer viewer notebook |
| `matplotlib-map-utils` | Map utilities |
| `matplotlib-scalebar` | Scale bar rendering |
| `nc-time-axis` | NetCDF time axis support (pip install via `environment.yml`) |
| `netCDF4` | NetCDF read/write |
| `numpy` | Numerical computation |
| `pandas` | DataFrame processing |
| `pyproj` | CRS transformation |
| `python=3.10` | Minimum Python version (conda) |
| `rasterio` | Raster I/O |
| `scikit-learn` | `LedoitWolf` covariance for Mahalanobis outlier detection |
| `scipy` | Statistical functions |
| `shapely` | Geometry construction |
| `tqdm` | Progress bars |
| `xarray` | NetCDF dataset handling |

> **Note:** `geopandas` is easiest to install via **conda-forge**. `cartopy`, `matplotlib`, and `matplotlib-map-utils` are required by the layer viewer notebook but not by the main pipeline script.

---

## Configuration (`config.json`)

All runs are driven by a JSON config file passed via `-c config.json`. Every key listed below is required — the script will exit with an error if any key is missing or unexpected.

### Input / batch settings

| Key | Type | Description |
|-----|------|-------------|
| `batch_process` | bool | If `true`, process all `.txt`/`.csv` files in `sar_drift_directory`; if `false`, process the single file at `sar_drift_filename` |
| `sar_drift_directory` | str | Directory containing gfilter input files (used when `batch_process` is `true`) |
| `sar_drift_filename` | str | Path to a single gfilter input file (used when `batch_process` is `false`) |
| `delimiter` | str | Field separator in the input file (e.g. `","`, `"\\t"`) |

### Output paths and templates

| Key | Type | Description |
|-----|------|-------------|
| `file_server` | str | Root path where daily outputs are written, structured as `<file_server>/<epsg>/<level_label>/<year>/<type>/` |
| `netcdf_cdl_file` | str | Path to the base CDL template file used to populate NetCDF metadata (e.g. `meta/sar_drift_output.cdl`); the pipeline derives the EPSG-specific variant automatically (e.g. `sar_drift_output_3413.cdl`) |
| `netcdf_template_file` | str | Path to the NSIDC polar stereographic NetCDF template providing the target grid |
| `outlier_qml_file` | str | Path to QML style file for outlier-category coloring in QGIS (applied for level `02`) |
| `graduated_qml_file` | str | Path to QML style file for graduated-speed coloring in QGIS (applied for all levels other than `02`) |
| `html_with_outlier_template` | str | Path to the HTML viewer template used to generate daily vector HTML output for levels that include outlier category display |
| `html_without_outlier_template` | str | Path to the HTML viewer template used to generate daily vector HTML output for levels without outlier display (e.g. level `03`) |
| `meta_dir` | str | Directory containing static reference files (`land.geojson`, `coastline.geojson`, `graticule.geojson`, `grid.json`) copied into the HTML `data/` subdirectory at runtime. Also contains CDL for NetCDF, HTML templates and QML files for GeoPackages |

> **Note:** `output_dir`, `formatted_data_dir`, `nc_dir`, and `filtered_data_dir` are **not** config.json keys. They are derived automatically by the script as subdirectories of `level_output/<level>/`.

### Optional GeoTIFF / plotting settings

These keys are required in the JSON even if the features are not in active use. Set booleans to `false` and numeric values to reasonable defaults.

| Key | Type | Description |
|-----|------|-------------|
| `use_geotiff` | bool | Enable GeoTIFF overlay workflow; if `false`, `sar_geotiff_filename` is not validated |
| `sar_geotiff_filename` | str | Path to a SAR backscatter GeoTIFF (only checked if `use_geotiff` is `true`) |
| `create_region_plot` | bool | Reserved for regional overview plot; stored in config but not currently active |
| `vector_stride` | int | Display every nth vector in plots (1 = all; ≥ 1) |
| `inlier_vector_stride` | int | Display every nth inlier vector in plots (≥ 1) |
| `quiver_scale_small_area` | float | Quiver arrow scale for small-area plots |
| `quiver_scale_large_area` | float | Quiver arrow scale for large-area plots |

### Run controls

| Key | Type | Description |
|-----|------|-------------|
| `clear_output_dir` | bool | If `true`, delete `level_output/<level>/` and all contents before the run |
| `overwrite` | bool | If `true`, rewrite all output files even if they already exist on disk; if `false`, any day whose file server outputs are all present is skipped entirely without running scene processing |
| `verbose` | bool | If `true`, print all resolved config parameters to stdout at startup |
| `version` | str | Version string included in output filenames (e.g. `"01"`) |

### EPSG projections and processing levels

EPSG codes and processing levels are **not** read from `config.json`. They are hardcoded in `process_level_output` and set on the config dict at runtime for each combination:

- **EPSG list:** `[3413, 6931]` — NSIDC North Polar Stereographic and EASE-Grid 2.0 North. Up to four EPSGs are supported.
- **Processing levels:** `['01', '02', '03']` in production; `['00']` in test mode.

| Level | Filtering | Outputs |
|-------|-----------|---------|
| `00` | None (testing) | NetCDF (multi-layer + single), GeoPackage, vector HTML/JSON |
| `01` | No hard row drops; invalid bearing/speed and `Maxcorr` quality captured as `bearing_error`, `speed_error`, and `measurement_error` flags | NetCDF (multi-layer + single) |
| `02` | **Per-row drops:** zero bearing/speed, speed above threshold, `Maxcorr2 ≤ Maxcorr1`. **Scene-level rejection:** < 60% valid Maxcorr or too few vectors | NetCDF (multi-layer + single), GeoPackage with outlier labels |
| `03` | Same as `02`, plus inlier-only filtering: retain `outlier_category` `00`/`01`, recode to `−1` | NetCDF (multi-layer + single), GeoPackage, vector HTML/JSON (inliers only) |

---

## Algorithm Parameters (`constants.py`)

Versioned algorithm parameters are defined in `constants.py` so that changes are tracked under version control independently of `config.json`. These values are loaded at startup and cannot be overridden via `config.json`.

### Filtering

| Parameter | Default | Description |
|-----------|---------|-------------|
| `IGNORE_VECTOR_THRESHOLD` | `1` | Discard scenes whose remaining vector count falls at or below this value after per-row filtering |
| `Z_SCORE_LEVEL` | `2.75` | Z-score threshold above which a vector is flagged as a speed or bearing outlier |
| `CHI_SQUARE_LEVEL` | `0.975` | Chi-square cumulative probability used to derive the squared Mahalanobis distance cutoff (`chi2.ppf(CHI_SQUARE_LEVEL, df=2)`) |

### Neighbor search

| Parameter | Default | Description |
|-----------|---------|-------------|
| `NEIGHBOR_RADIUS_KM` | `25.0` | Radius in kilometres for spatial neighbor lookup via `cKDTree.query_ball_point` |
| `MIN_NEIGHBORS` | `8` | Minimum neighbors required to mark a z-score outlier result as statistically confident (units digit `1`) |
| `MD_MIN_NEIGHBORS` | `24` | Minimum neighbors required to mark a Mahalanobis distance outlier result as statistically confident |
| `OUTLIER_PASSES` | `3` | Maximum number of iterative outlier detection passes; each pass rebuilds the neighbor pool using only current inliers |

### Rounding (applied in `_apply_projection`)

| Parameter | Default | Columns affected |
|-----------|---------|-----------------| 
| `COORDINATE_PRECISION` | `4` | `X1`, `Y1`, `X2`, `Y2` |
| `DISPLACEMENT_PRECISION` | `4` | `sea_ice_x_displacement`, `sea_ice_y_displacement`, `u`, `v` |
| `SPEED_PRECISION` | `1` | `sea_ice_speed`, `sea_ice_speed_kmdy`, `distance`, `distance_geod` |
| `BEARING_PRECISION` | `0` | `direction_of_sea_ice_displacement` |

> **Note:** Rounding is applied with `numpy.round()` immediately after projection. `SPEED_PRECISION = 1` means speed values like `0.0592 m s⁻¹` are stored as `0.1` in the CSV and GeoPackage. Use the unrounded `u` / `v` components to verify speed independently: `SQRT(u² + v²) × 86400 / 1000` reproduces `sea_ice_speed_kmdy` before rounding.

---

## Usage

```bash
python sar_drift_converter.py -c config.json
```

The script:

1. Parses and validates `config.json` (`read_json_config`)
2. Compresses any existing `.log` files in `log_dir` to `.zip` archives, then initializes a fresh timestamped log file
3. Glob-matches input `.txt`/`.csv` files from `sar_drift_directory`, or loads the single file at `sar_drift_filename`
4. Reads all gfilter drift files in parallel into a single combined raw DataFrame (`combine_into_dataframe`); for each 50 km file, automatically substitutes the corresponding 75 km file if one exists. Header row position is detected automatically per file via `_detect_skip_rows` — no configuration key is required
5. Applies the EPSG-dependent coordinate projection once per EPSG (`_apply_projection`), producing one projected DataFrame per target CRS. This separation means the expensive parallel file I/O runs exactly once regardless of how many EPSGs are processed
6. For each level/EPSG combination, applies per-row and scene-level quality filters (`filter_input_data`)
7. Groups observations by calendar day of `date_start`
8. For each day, checks which expected file server outputs already exist (`check_existing_files`); if all outputs are present and `overwrite` is `false`, the day is skipped entirely
9. For each day requiring processing, processes all File1/File2 scene pairs (`create_scene_output`):
   - Writes a per-scene formatted CSV
   - Runs outlier detection (always, even if NetCDF already exists, since `df_scenes` is needed for GeoPackage and HTML)
   - Writes per-scene NetCDF files only if either daily NetCDF variant is missing
   - Accumulates all post-outlier-detection rows into a combined `df_scenes` DataFrame
10. Produces daily outputs from `df_scenes` (`create_daily_output`), skipping any output type whose file already exists:
    - Two NetCDF files: a multi-layered scenes file and a single-layer daily mosaic
    - One GeoPackage (levels `00`, `02`, `03`)
    - One vector HTML + companion JSON file (levels `00`, `03`)
    - Two formatted CSVs: `<start>_<end>_raw.csv` and `<start>_<end>_processing_codes.csv` (always written)

### Daily output filename convention

```
SIVelocity_SAR_<YYYYMMDD>_<YYYYMMDD>_<type>_12km_NH_<epsg>_PL<level>_v<version>.<ext>
```

where `<type>` is `scenes` for the multi-layered NetCDF and `daily` for all other output types. Files are written to:

```
<file_server>/<epsg>/<level_label>/<year>/<type>/
```

For example, a level `03` daily GeoPackage for 2024-12-30:

```
SIVelocity_SAR/3413/Processing Level - 03 (PL03)/2024/gpkg/SIVelocity_SAR_20241230_20241231_daily_12km_NH_3413_PL03_v01.gpkg
```

### Local output subdirectory structure

Created automatically under `level_output/<level>/`:

| Directory | Contents |
|-----------|----------|
| `filtered_data/` | Unfiltered combined CSV (level `00` only) |
| `formatted_data/` | Per-scene formatted CSVs; daily `_raw.csv` and `_processing_codes.csv` |
| `nc/` | Per-scene NetCDF files |

Daily GeoPackage, vector HTML/JSON, and final NetCDF mosaics are written to `file_server` subdirectories, not to `level_output/`.

---

## Outputs

For a batch run covering 2024-12-30 at level `03`:

**Local intermediate outputs** (`level_output/3/`):
- `formatted_data/formatted_<scene_id>.csv` — one per scene pair
- `formatted_data/20241230_20241231_raw.csv` — all input rows for the day
- `formatted_data/20241230_20241231_processing_codes.csv` — post-outlier-detection rows with codes
- `nc/<scene_id>.nc` — one per scene pair

**File server daily outputs** (`SIVelocity_SAR/3413/Processing Level - 03 (PL03)/2024/`):
- `nc/SIVelocity_SAR_20241230_20241231_scenes_12km_NH_3413_PL03_v01.nc`
- `nc/SIVelocity_SAR_20241230_20241231_daily_12km_NH_3413_PL03_v01.nc`
- `gpkg/SIVelocity_SAR_20241230_20241231_daily_12km_NH_3413_PL03_v01.gpkg`
- `html/SIVelocity_SAR_20241230_20241231_daily_12km_NH_3413_PL03_v01_vector.html`
- `html/data/si_velocity_20241230.json`

---

## Variable Reference

Variables flow through three stages: raw columns read from the gfilter source file, derived columns computed during pipeline processing, and variables written to the NetCDF and GeoPackage outputs.

### CSV source — raw input columns

Columns marked *dropped* are consumed during processing but not carried forward into any output file.

| Column | Units | Retained | Description |
|--------|-------|----------|-------------|
| `File1` | — | ✓ | Filename of the first SAR scene (start image) |
| `File2` | — | ✓ | Filename of the second SAR scene (end image) |
| `Time1_JS` | s | dropped | Start time as Julian seconds since 2000-01-01 00:00:00 |
| `Time2_JS` | s | dropped | End time as Julian seconds since 2000-01-01 00:00:00 |
| `Lon1` | degrees | renamed → `longitude_1` | Starting longitude of the tracked ice feature |
| `Lat1` | degrees | renamed → `latitude_1` | Starting latitude of the tracked ice feature |
| `Lon2` | degrees | renamed → `longitude_2` | Ending longitude of the tracked ice feature |
| `Lat2` | degrees | renamed → `latitude_2` | Ending latitude of the tracked ice feature |
| `Bear_deg` | degrees | dropped | Source-file bearing; used in `filter_input_data` to remove zero-bearing rows, then dropped |
| `Speed_kmdy` | km/day | dropped | Source-file speed; used in `filter_input_data` for speed threshold filtering, then dropped |
| `U_vel_ms` | m s⁻¹ | dropped | Source-file x-velocity component; dropped after read (recomputed from projected coordinates) |
| `V_vel_ms` | m s⁻¹ | dropped | Source-file y-velocity component; dropped after read (recomputed from projected coordinates) |
| `Maxcorr1` | — | ✓ | Cross-correlation score of the first (lower-ranked) match candidate |
| `Maxcorr2` | — | ✓ | Cross-correlation score of the second (best) match candidate; must exceed `Maxcorr1` for the row to pass filtering |
| `img1_mean`, `img1_std` | — | dropped | Image 1 patch mean and standard deviation |
| `img2_mean`, `img2_std` | — | dropped | Image 2 patch mean and standard deviation |
| `img1s_mean`, `img1s_std` | — | dropped | Image 1 sub-patch mean and standard deviation |
| `Npnt` | — | dropped | Number of points used in the correlation |
| `Offset1`, `Offset2` | — | dropped | Correlation offset values |

### Derived — computed in pipeline

These columns are added by `read_sar_drift_data_file`, `_apply_projection`, and `outlier_search` and are carried through all downstream processing.

`read_sar_drift_data_file` adds the EPSG-independent columns (timestamps, duration, identifiers, raw coordinates). `_apply_projection` adds all projection-dependent columns for a specific target EPSG. This two-step design allows the expensive file I/O to run once while projections are applied cheaply per EPSG from the already-loaded DataFrame.

| Column | CRS / Reference | Units | Description |
|--------|----------------|-------|-------------|
| `scene_id` | — | — | Combination of `File1` and `File2` joined by `_`; used to group observations into scene pairs |
| `date_start` | — | — | Start datetime converted from `Time1_JS` (format: `YYYY-MM-DD HH:MM:SS`) |
| `date_end` | — | — | End datetime converted from `Time2_JS` |
| `duration` | — | s | Observation duration (`Time2_JS − Time1_JS`) |
| `longitude_1` | EPSG:4326 | degrees | Starting longitude (renamed from `Lon1`) |
| `latitude_1` | EPSG:4326 | degrees | Starting latitude (renamed from `Lat1`) |
| `longitude_2` | EPSG:4326 | degrees | Ending longitude (renamed from `Lon2`) |
| `latitude_2` | EPSG:4326 | degrees | Ending latitude (renamed from `Lat2`) |
| `sensor1` | — | — | Satellite identifier extracted from `File1` (prefix before first underscore) |
| `sensor2` | — | — | Satellite identifier extracted from `File2` |
| `X1` | EPSG:`config['epsg']` | m | Projected x-coordinate of start position |
| `Y1` | EPSG:`config['epsg']` | m | Projected y-coordinate of start position |
| `X2` | EPSG:`config['epsg']` | m | Projected x-coordinate of end position |
| `Y2` | EPSG:`config['epsg']` | m | Projected y-coordinate of end position |
| `sea_ice_x_displacement` | EPSG:`config['epsg']` | m | X displacement (`X2 − X1`); rounded to `displacement_precision` decimal places |
| `sea_ice_y_displacement` | EPSG:`config['epsg']` | m | Y displacement (`Y2 − Y1`); rounded to `displacement_precision` decimal places |
| `u` | EPSG:`config['epsg']` | m s⁻¹ | X-component of velocity (`sea_ice_x_displacement / duration`); rounded to `displacement_precision` decimal places |
| `v` | EPSG:`config['epsg']` | m s⁻¹ | Y-component of velocity (`sea_ice_y_displacement / duration`); rounded to `displacement_precision` decimal places |
| `sea_ice_speed` | geodesic | m s⁻¹ | Drift speed from geodesic distance / `duration`; rounded to `speed_precision` decimal places |
| `sea_ice_speed_kmdy` | geodesic | km/day | Drift speed in km/day from geodesic distance; rounded to `speed_precision` decimal places |
| `direction_of_sea_ice_displacement` | geodesic | degrees | Forward azimuth from geodesic inverse calculation (WGS84); rounded to `bearing_precision` decimal places |
| `distance` | EPSG:`config['epsg']` | m | Euclidean displacement distance in projected space: `sqrt(dx² + dy²)` |
| `distance_geod` | geodesic | m | Geodesic distance between start and end positions (WGS84); rounded to `speed_precision` decimal places |
| `outlier_category` | — | — | Two-digit outlier code (see [Outlier detection](#outlier-detection)); `−1` = inlier, outlier filter already applied (level `03`); fill = `−9` (level `01`) |
| `bearing_error` | — | — | `1` if `direction_of_sea_ice_displacement == 0` or `sea_ice_speed == 0`; `0` = valid; `−9` = not computed (levels `02`/`03`) |
| `speed_error` | — | — | `1` if speed exceeds threshold (25 km/day for 50 km files; 35 km/day for 75 km files); `0` = valid; `−9` = not computed (levels `02`/`03`) |
| `measurement_error` | — | — | `1` if `Maxcorr1 > Maxcorr2`; `0` = valid; `−9` = not computed (levels `02`/`03`) |

### NetCDF output variables

All gridded data variables have dimensions `(time, y, x)` projected on the NSIDC 12.5 km polar stereographic grid (EPSG:3413). Coordinates and auxiliary variables are also listed.

| Variable | Dimensions | Type | Units | Description |
|----------|------------|------|-------|-------------|
| `sea_ice_speed` | (time, y, x) | float32 | m s⁻¹ | Gridded sea ice drift speed |
| `sea_ice_x_displacement` | (time, y, x) | float32 | m | X-component of ice displacement |
| `sea_ice_y_displacement` | (time, y, x) | float32 | m | Y-component of ice displacement |
| `direction_of_sea_ice_displacement` | (time, y, x) | float32 | degrees | Drift direction (forward azimuth) |
| `outlier_category` | (time, y, x) | int16 | — | Outlier classification code; `−1` = inlier, outlier filter already applied (level `03`); fill value = `−9` |
| `bearing_error` | (time, y, x) | int16 | — | Bearing validity flag; fill value = `−9` |
| `speed_error` | (time, y, x) | int16 | — | Speed threshold flag; fill value = `−9` |
| `measurement_error` | (time, y, x) | int16 | — | Cross-correlation quality flag; fill value = `−9` |
| `layer_id` *(coord)* | (time) | char | — | Scene identifier string for each time layer; set as a coordinate of `time` via `time:coordinates = 'layer_id'` |
| `spatial_ref` | scalar | int32 | — | CRS container variable holding WKT/proj4 projection metadata |
| `time_bnds` | (time, nv=2) | float64 | s | CF time bounds: `[min(date_start), max(date_end)]` in seconds since 2000-01-01 |
| `time` *(coord)* | (time) | float64 | s | Scene reference time: `min(date_start)` in seconds since 2000-01-01 |
| `x` *(coord)* | (x) | float64 | m | x-coordinates of the 12.5 km polar stereographic grid |
| `y` *(coord)* | (y) | float64 | m | y-coordinates of the 12.5 km polar stereographic grid |

### GeoPackage output columns

Layer name: `drift_lines`. CRS: EPSG:`config['epsg']`. Geometry: `LineString` from `(X1, Y1)` to `(X2, Y2)` in projected metres. One GeoPackage is produced per day, combining all scene pairs.

| Column | CRS / Reference | Units | Description |
|--------|----------------|-------|-------------|
| `scene_id` | — | — | Scene pair identifier (`File1_File2`) |
| `sensor1` | — | — | Satellite identifier for the start scene |
| `sensor2` | — | — | Satellite identifier for the end scene |
| `longitude_1` | EPSG:4326 | degrees | Starting longitude |
| `latitude_1` | EPSG:4326 | degrees | Starting latitude |
| `longitude_2` | EPSG:4326 | degrees | Ending longitude |
| `latitude_2` | EPSG:4326 | degrees | Ending latitude |
| `X1` | EPSG:`config['epsg']` | m | Projected x-coordinate of start position |
| `Y1` | EPSG:`config['epsg']` | m | Projected y-coordinate of start position |
| `X2` | EPSG:`config['epsg']` | m | Projected x-coordinate of end position |
| `Y2` | EPSG:`config['epsg']` | m | Projected y-coordinate of end position |
| `date_start` | — | — | Start datetime string (`YYYY-MM-DD HH:MM:SS`) |
| `date_end` | — | — | End datetime string (`YYYY-MM-DD HH:MM:SS`) |
| `duration` | — | s | Observation duration in seconds |
| `sea_ice_x_displacement` | EPSG:`config['epsg']` | m | X displacement |
| `sea_ice_y_displacement` | EPSG:`config['epsg']` | m | Y displacement |
| `u` | EPSG:`config['epsg']` | m s⁻¹ | X-component of velocity |
| `v` | EPSG:`config['epsg']` | m s⁻¹ | Y-component of velocity |
| `sea_ice_speed` | geodesic | m s⁻¹ | Drift speed |
| `sea_ice_speed_kmdy` | geodesic | km/day | Drift speed in km/day |
| `direction_of_sea_ice_displacement` | geodesic | degrees | Drift direction |
| `distance` | geodesic | m | Euclidean displacement distance in projected space: sqrt(dx² + dy²) |
| `distance_geod` | geodesic | m | Geodesic displacement distance on the WGS84 ellipsoid |
| `outlier_category` | — | — | Two-digit outlier code; `−1` = inlier filter applied (level `03`); included only in levels `00`, `02`, and `03` |
| `geometry` | EPSG:`config['epsg']` | — | `LineString` from `(X1, Y1)` to `(X2, Y2)` in projected metres |
| `geometry_type` | — | — | Literal string `'line'` identifying the layer geometry type |

### Vector HTML output

One interactive HTML file and a companion JSON data file are produced per day (levels `00` and `03`), combining all scene pairs for that day. The HTML viewer renders drift vectors on an interactive Leaflet polar stereographic map. For level `03`, only inlier vectors (`outlier_category` `00`/`01`) are written and their `outlier_category` is recoded to `−1`.

The JSON file is written to a `data/` subdirectory alongside the HTML file and contains date metadata and a compact vector list:

```json
{
  "date1": "YYYY-MM-DD",
  "date2": "YYYY-MM-DD",
  "count": <int>,
  "vectors": [[lon1, lat1, lon2, lat2, speed_x100, outlier_category], ...]
}
```

where `speed_x100` is drift speed in km/day multiplied by 100 and rounded to the nearest integer. The `data/` subdirectory also receives static GeoJSON reference files (land, coastline, graticule, grid) copied from `config['meta_dir']` at runtime.

---

## Outlier detection

The main outlier routine is `util.outlier_search(...)`. It supports two methods:

- **Z-score** on drift distance and bearing, computed within a spatial neighborhood
- **Mahalanobis distance** using `LedoitWolf` covariance estimation (`sklearn.covariance.LedoitWolf`) on velocity components

Key ideas:

- Neighbors are found **within each scene** (grouped by `File1`/`File2`)
- Neighborhoods are computed with a **radius search** (km) using `cKDTree.query_ball_point`
- `outlier_category` encodes **outlier type** and **statistical confidence** (whether the neighbor threshold was met):

| Code | Outlier Type | Neighbor Threshold Met |
|------|-------------|----------------------|
| `−1` | None (inlier — outlier filter already applied, level `03` only) | — |
| `00` | None | No |
| `01` | None | Yes |
| `10` | Distance | No |
| `11` | Distance | Yes |
| `20` | Bearing | No |
| `21` | Bearing | Yes |
| `30` | Mahalanobis Distance | No |
| `31` | Mahalanobis Distance | Yes |
| `40` | Distance and Bearing | No |
| `41` | Distance and Bearing | Yes |
| `50` | Mahalanobis Distance and Distance | No |
| `51` | Mahalanobis Distance and Distance | Yes |
| `60` | Mahalanobis Distance and Bearing | No |
| `61` | Mahalanobis Distance and Bearing | Yes |
| `70` | Mahalanobis Distance, Distance and Bearing | No |
| `71` | Mahalanobis Distance, Distance and Bearing | Yes |

### Level `03` inlier filtering

For level `03` outputs, `create_shape_package`, `create_vector_html_and_json`, and `create_netcdf` apply the following steps before writing:

1. Retain only rows where `outlier_category` is `'00'` or `'01'` (confirmed inliers).
2. Recode all retained rows' `outlier_category` to `−1`, signaling that the outlier algorithm has been applied and these vectors passed as inliers.
3. If no rows survive the filter, the output file is skipped and the function returns `None`.

### Iterative passes

For each pass in `OUTLIER_PASSES`, only vectors with `outlier_category in ['00', '01']` are used as the neighbor pool when recomputing statistics. This prevents already-flagged vectors from influencing local statistics in subsequent passes.

---

## Output quality notes

- **75 km file preference:** For each 50 km gfilter file, the pipeline automatically checks for a corresponding 75 km file (same name with `_0050000m_` replaced by `_0075000m_`). If found, the 75 km file is read instead, improving spatial coverage. The speed anomaly threshold is adjusted accordingly (25 km/day for 50 km files, 35 km/day for 75 km files).
- **Zero std:** `outlier_search` guards against `dist_std == 0` or `bear_std == 0` to avoid divide-by-zero in z-score computation.
- **Header auto-detection:** `_detect_skip_rows` peeks at up to the first 10 lines of each input file to locate the header row (identified by the presence of `'File1'` and `'File2'`), returning the number of rows to skip before it. This handles files that include preamble lines before the header. No configuration key is required — detection runs automatically for every file.
- **Parallel file reads:** `combine_into_dataframe` uses `ProcessPoolExecutor` to read all input files in parallel across CPU cores (default: `min(32, os.cpu_count())`). For large batches (~75,000 files) this reduces read time from ~15 minutes to ~1–2 minutes on a 16-core machine. If a file fails to read, the exception propagates immediately and processing halts.
- **Single read, multiple projections:** Input files are read once into a single raw DataFrame. Projection to each target EPSG is applied separately via `_apply_projection` after all files are combined. This avoids re-reading 75,000 files for each EPSG combination.
- **Partial day resume:** When `overwrite` is `false`, `check_existing_files` returns a per-output-type existence dict. Days where only some outputs are missing are partially reprocessed — outlier detection always runs to produce `df_scenes`, per-scene NetCDF files are written only if either daily NetCDF variant is missing, and each daily output type is written independently based on its existence flag.

---

## Notebooks

### `sar_sea_ice_drift_netcdf_layer_viewer.ipynb`

An interactive Jupyter notebook for exploring and exporting individual time layers from the daily SAR sea-ice drift NetCDF product.

**What it does:**

- Opens a NetCDF file and displays a high-level dataset summary
- Lists all `layer_id` values so a layer can be located by scene ID or index
- Computes per-variable statistics (shape, valid count, min/max/mean/std) for a selected layer
- Exports a selected layer to a **GeoPackage** (`drift_lines`, EPSG:`epsg`) with an embedded QGIS QML style
- Renders a **quiver plot PNG** of drift vectors on a Cartopy basemap; the Cartopy projection is selected dynamically based on `epsg` (North Polar Stereographic for EPSG:3413/3411; Lambert Azimuthal Equal-Area for EPSG:6931)

**Key parameters (set by the user):**

| Parameter | Description |
|-----------|-------------|
| `nc_path` | Path to the input NetCDF file |
| `selected_layer_index` | Integer index of the time layer to export/plot |
| `has_outliers` | `True` for level `02` files (colors arrows by outlier category); `False` for levels `01`/`03` (colors by displacement magnitude) |
| `epsg` | EPSG code of the projected CRS used in the NetCDF file (e.g. `3413`, `6931`); controls GeoPackage layer CRS and Cartopy projection |

**Outputs written to disk:**

| File | Location | Description |
|------|----------|-------------|
| `<layer_id>.gpkg` | `layer_to_gpkg/` | GeoPackage with `drift_lines` layer in EPSG:`epsg` and embedded QML style |

The PNG plot can be saved locally by right-clicking the inline image and choosing *Save Image As*.

---

## Quick checklist

1. Update `config.json` paths (`sar_drift_directory`, `file_server`, `netcdf_template_file`, `netcdf_cdl_file`, `html_with_outlier_template`, `html_without_outlier_template`, `meta_dir`, QML files)
2. Run `python sar_drift_converter.py -c config.json`
3. Open the daily `.gpkg` in QGIS to verify vector placement and styling
4. Open the daily `_vector.html` in a browser (served via `python -m http.server`) to verify the interactive map
5. Validate `.nc` metadata and grid (both `_scenes_` and `_daily_` variants)
