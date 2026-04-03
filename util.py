# -*- coding: utf-8 -*-
"""
******************************************************************************

 Project:    SAR Drift Velocity over MOSAiC Vectors
 Purpose:    Utility functions that support the main script
 Author:     Brendon Gory, brendon.gory@noaa.gov
                         brendon.gory@colostate.edu
             Data Science Application Specialist (Research Associate II)
             at CSU CIRA
 Supervisor: Dr. Prasanjit Dash, prasanjit.dash@noaa.gov
                                 prasanjit.dash@colostate.edu
             CSU CIRA Research Scientist III
             (Program Innovation Scientist)
******************************************************************************
Copyright notice
         NOAA STAR SOCD and Colorado State Univ CIRA
         2025, Version 1.0.0
         POC: Brendon Gory (brendon.gory@noaa.gov)

 Permission is hereby granted, free of charge, to any person obtaining a
 copy of this software and associated documentation files (the "Software"),
 to deal in the Software without restriction, including without limitation
 the rights to use, copy, modify, merge, publish, distribute, sublicense,
 and/or sell copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included
 in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 DEALINGS IN THE SOFTWARE.
"""

import os
import sys
from pathlib import Path

# Derive paths from the active env rather than hard-coding
env_prefix = Path(sys.prefix)
proj_dir = env_prefix / "Library" / "share" / "proj"
bin_dir = env_prefix / "Library" / "bin"

# print("Using PROJ dir:", proj_dir)
# print("Using bin dir:", bin_dir)

os.add_dll_directory(str(bin_dir))

# Set both env vars for PROJ
os.environ["PROJ_DATA"] = str(proj_dir)
os.environ["PROJ_LIB"] = str(proj_dir)   # backward compatibility

# Tell pyproj explicitly where proj.db lives
from pyproj.datadir import set_data_dir
set_data_dir(str(proj_dir))

from pyproj import CRS, Transformer, Geod

#=========================
# Standard error messaging
#=========================

def error_msg(msg):
    """
    Print an error message with a warning icon and exit the program.

    Parameters
    ----------
    msg : str
        The error message to display in the console.

    Notes
    -----
    - This function immediately terminates the program using `exit()`.
    """

    
    print(f"  ⚠️ {msg}")
    exit()
    
    
#===================
# Internal functions
#===================

def _set_transformer(epsg=3413):
    transformer = {}
    
    # CRS setup
    transformer['epsg'] = epsg
    transformer['crs_string_3413'] = CRS.from_string(
        "+proj=stere +lat_0=90 +lat_ts=70 +lon_0=-45 "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs"
    )
    transformer['crs_string_4326'] = CRS.from_string(
        "+proj=longlat +datum=WGS84 +no_defs +type=crs"
    )
    transformer["crs_string_3408"] = CRS.from_string(
        "+proj=laea +lat_0=90 +lon_0=0 "
        "+x_0=0 +y_0=0 "
        "+a=6371228 +b=6371228 "
        "+units=m +no_defs +type=crs"
    )
    
    transformer["crs_string_3411"] = CRS.from_string(
        "+proj=stere +lat_0=90 +lat_ts=70 +lon_0=-45 "
        "+x_0=0 +y_0=0 +a=6378273 +b=6356889.449 "
        "+units=m +no_defs +type=crs"
    )
    
    transformer['proj4_3413_dict'] = {
        "proj": "stere",
        "lat_0": 90,
        "lat_ts": 70,
        "lon_0": -45,
        "x_0": 0,
        "y_0": 0,
        "datum": "WGS84",
        "units": "m",
        "no_defs": True
    }
    
    transformer['4326_to_3413'] = Transformer.from_crs(
        transformer['crs_string_4326'],
        transformer['crs_string_3413'],
        always_xy=True
    )

    transformer['3413_to_4326'] = Transformer.from_crs(
        transformer['crs_string_3413'],
        transformer['crs_string_4326'],
        always_xy=True
    )
    
    transformer['4326_to_3408'] = Transformer.from_crs(
        transformer['crs_string_4326'],
        transformer['crs_string_3408'],
        always_xy=True
    )
    
    transformer['4326_to_3411'] = Transformer.from_crs(
        transformer['crs_string_4326'],
        transformer['crs_string_3411'],
        always_xy=True
    )
    
    return transformer
        

def _calculate_drift_daily(lat1, lon1, lat2, lon2, duration_s):
    """
    Compute sea-ice drift kinematics from start/end geographic coordinates.
 
    Projects start and end positions from EPSG:4326 to EPSG:3413 (NSIDC Sea
    Ice Polar Stereographic North), computes Cartesian displacement components,
    and derives speed. Bearing is obtained a WGS84 geodesic inverse
    calculation.
 
    Args:
        lat1 (array-like): Starting latitudes in decimal degrees (EPSG:4326).
        lon1 (array-like): Starting longitudes in decimal degrees (EPSG:4326).
        lat2 (array-like): Ending latitudes in decimal degrees (EPSG:4326).
        lon2 (array-like): Ending longitudes in decimal degrees (EPSG:4326).
        duration_s (array-like): Observation duration in seconds
                                  (Time2_JS − Time1_JS).
 
    Returns:
        dict: Dictionary of derived drift quantities with the following keys:
 
            Projected coordinates (EPSG:3413, metres):
                - 'X1' : x-coordinate of start position
                - 'Y1' : y-coordinate of start position
                - 'X2' : x-coordinate of end position
                - 'Y2' : y-coordinate of end position
 
            Displacement (EPSG:3413, metres):
                - 'dx' : X2 − X1
                - 'dy' : Y2 − Y1
 
            Geodesic quantities:
                - 'distance'  : geodesic distance between start and end (m)
                - 'bearing'   : forward azimuth from start to end (degrees)
 
            Velocity components (EPSG:3413):
                - 'u_ms' : dx / duration_s  (m s⁻¹)
                - 'v_ms' : dy / duration_s  (m s⁻¹)
 
            Speed:
                - 'speed_ms'   : distance / duration_s (m s⁻¹)
                - 'speed_kmdy' : (distance / 1000) / (duration_s / 86400)
                                  (km day⁻¹)
 
    Notes:
        - Projection is performed with `pyproj.Transformer` using
          `always_xy=True`, so longitude is passed before latitude.
        - Geodesic distance and forward azimuth are computed with
          `pyproj.Geod(ellps='WGS84').inv(lon1, lat1, lon2, lat2)`.
        - `u_vel_ms` and `v_vel_ms` are Cartesian velocity components in
          EPSG:3413 projection space. In this projection the x-axis points
          roughly eastward and the y-axis roughly northward, but note that
          the source file's `U_vel_ms` / `V_vel_ms` fields use the opposite
          convention (U drives Y, V drives X). The values returned here are
          computed directly from projected displacements and are
          self-consistent.
          
    Coauthor:
        Ludo Brucker, ludovic.brucker@noaa.gov        
    """    
    import numpy as np
   
    SECONDS_PER_DAY = 60 * 60 * 24
    tf = Transformer.from_crs('EPSG:4326', 'EPSG:3413', always_xy=True)
    
    x1, y1 = tf.transform(lon1, lat1)
    x2, y2 = tf.transform(lon2, lat2)
   

    dx, dy = np.subtract((x2, y2),(x1, y1))

    geod = Geod(ellps='WGS84')
    fwd_azimuth, _ , distance = geod.inv(lon1, lat1, lon2, lat2)
    
    return {
        'X1': x1, 'Y1': y1,
        'X2': x2, 'Y2': y2,
        'dx': dx,
        'dy': dy,
        'distance': distance,
        'bearing': fwd_azimuth,
        'u_ms': dx / duration_s,
        'v_ms': dy / duration_s,
        'speed_ms': distance / duration_s,
        'speed_kmdy': (distance / 1000) / (duration_s / SECONDS_PER_DAY)
    }


def _embed_qml_style(gpkg_path, layer_name, qml_path):
    """
    Embed a QML style into a GeoPackage's layer_styles table.

    Reads a QML file and writes its contents into the QGIS-standard
    layer_styles table inside the GeoPackage. QGIS will automatically
    apply the style when the layer is loaded, requiring no QML file
    on the end user's machine.

    Args:
        gpkg_path (str): Full path to the target GeoPackage file.
        layer_name (str): Name of the layer to apply the style to.
                          Must match the layer name in the GeoPackage exactly.
        qml_path (str): Full path to the QML style file to embed.

    Returns:
        None

    Notes:
        - The layer_styles table is created if it does not already exist,
          following the QGIS standard schema.
        - `f_geometry_column` is hardcoded to 'geom' because GeoPandas
          silently renames the geometry column from 'geometry' to 'geom'
          when writing to GeoPackage format.
        - `useAsDefault` is set to 1 so QGIS applies the style automatically
          on load without user intervention.
        - The layer_styles table is registered in gpkg_contents as an
          attributes layer for full GeoPackage spec compliance.
    """
    import sqlite3
    
    with open(qml_path, 'r') as f:
        qml_content = f.read()

    conn = sqlite3.connect(gpkg_path)
    cursor = conn.cursor()

    # Create layer_styles table if it doesn't exist (QGIS standard schema)
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS layer_styles (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       f_table_catalog TEXT,
                       f_table_schema TEXT,
                       f_table_name TEXT,
                       f_geometry_column TEXT,
                       styleName TEXT,
                       styleQML TEXT,
                       styleSLD TEXT,
                       useAsDefault INTEGER,
                       description TEXT,
                       owner TEXT,
                       ui TEXT,
                       update_time DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
    )


    cursor.execute("""
                   INSERT INTO layer_styles 
                   (f_table_catalog, f_table_schema, f_table_name, 
                    f_geometry_column, styleName, styleQML, styleSLD,
                    useAsDefault, description, owner)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   """,
                   (
                       '',           # f_table_catalog
                       '',           # f_table_schema
                       layer_name,   # f_table_name  
                       'geom',       # f_geometry_column
                       'outliers',   # styleName
                       qml_content,  # styleQML
                       '',           # styleSLD (leave blank)
                       1,            # useAsDefault
                       '',
                       ''
                    )
    )
    
    cursor.execute("""
                   INSERT OR IGNORE INTO gpkg_contents 
                   (table_name, data_type, identifier, description,
                    last_change)
                   VALUES 
                   ('layer_styles', 'attributes', 'layer_styles',
                    'QGIS layer styles', datetime('now'))
                   """
    )

    conn.commit()    
    conn.close()
    
    
#=========
# Data I/O
#=========

def read_sar_drift_data_file(input_file, config, skip_rows=None):
    """
    Read and preprocess a SAR ice-drift text data file into a standardized
    DataFrame.
 
    This function loads a SAR drift data file (CSV-like text) using parsing
    rules provided in `config`, cleans column names, and derives projected
    coordinates, displacement, velocity, speed, and sensor identifier fields.
    Several raw source columns are renamed for consistency with NetCDF/
    GeoPackage output naming, and columns that are not needed downstream
    are dropped.
 
    Processing steps:
        1. Read the file with `pandas.read_csv()` using delimiter and header
           offsets from `config`.
        2. Strip whitespace from column names.
        3. Convert Julian seconds timestamps (`Time1_JS`, `Time2_JS`) to
           human-readable datetime strings (`date_start`, `date_end`).
        4. Compute observation duration in seconds (`duration_s`).
        5. Project start/end lat/lon to EPSG:3413 and compute displacement,
           velocity, speed, and bearing via `_calculate_drift_daily`.
        6. Round computed fields according to precision keys in `config`:
               coordinates_position : Lat1, Lon1, Lat2, Lon2, X1, Y1, X2, Y2
               speed_precision      : sea_ice_x_displacement,
                                      sea_ice_y_displacement, sea_ice_speed,
                                      sea_ice_speed_kmdy, distance
               bearing_precision    : direction_of_sea_ice_displacement
               u_ms, v_ms are not rounded.
        7. Extract sensor identifiers from `File1`/`File2` into `sensor1`/
           `sensor2`.
        8. Rename geographic coordinate columns:
               Lat1 → latitude_1,  Lon1 → longitude_1
               Lat2 → latitude_2,  Lon2 → longitude_2
        9. Drop source columns that are not used in any output:
               File1, File2, Time1_JS, Time2_JS, U_vel_ms, V_vel_ms,
               Speed_kmdy, Bear_deg, img1_mean, img1_std, img2_mean,
               img2_std, img1s_mean, img1s_std, Per_Valid
 
    Args:
        input_file (str or pathlib.Path): Path to the SAR drift data file
                                          to read.
        config (dict): Parsing and precision configuration. Expected keys:
            - 'delimiter' (str): Field delimiter passed to `pd.read_csv`.
            - 'skip_rows_before_header' (int): Number of rows to skip before
              the header row.
            - 'coordinates_position' (int): Decimal places for geographic
              coordinates (Lat1, Lon1, Lat2, Lon2) and projected coordinates
              (X1, Y1, X2, Y2).
            - 'speed_precision' (int): Decimal places for
              `sea_ice_x_displacement`, `sea_ice_y_displacement`,
              `sea_ice_speed`, `sea_ice_speed_kmdy`, and `distance`.
            - 'bearing_precision' (int): Decimal places for
              `direction_of_sea_ice_displacement`.
        skip_rows (list[int] or None): Row indices to skip when reading the
            file, passed directly to `pd.read_csv`. Defaults to None.
 
    Returns:
        pandas.DataFrame: Cleaned and enriched SAR drift DataFrame. Raw source
        columns are preserved (except those listed as dropped above) together
        with the following derived and renamed columns:
 
        Renamed geographic coordinates (rounded to `coordinates_position`):
            - 'latitude_1'  (float): Starting latitude  (degrees, from Lat1)
            - 'longitude_1' (float): Starting longitude (degrees, from Lon1)
            - 'latitude_2'  (float): Ending latitude    (degrees, from Lat2)
            - 'longitude_2' (float): Ending longitude   (degrees, from Lon2)
 
        Derived timestamps and duration:
            - 'date_start' (str): Start datetime in '%Y-%m-%d %H:%M:%S'
                                  (from Time1_JS)
            - 'date_end'   (str): End datetime in '%Y-%m-%d %H:%M:%S'
                                  (from Time2_JS)
            - 'duration_s' (float): Observation duration in seconds
                                    (Time2_JS − Time1_JS); not rounded.
 
        Projected coordinates (EPSG:3413, metres; rounded to
        `coordinates_position`):
            - 'X1', 'Y1': Start position
            - 'X2', 'Y2': End position
 
        Displacement (EPSG:3413; rounded to `speed_precision`):
            - 'sea_ice_x_displacement' (float): X2 − X1  (m)
            - 'sea_ice_y_displacement' (float): Y2 − Y1  (m)

        Velocity (EPSG:3413; not rounded):
            - 'u_ms' (float): sea_ice_x_displacement / duration_s  (m s⁻¹)
            - 'v_ms' (float): sea_ice_y_displacement / duration_s  (m s⁻¹)
 
        Speed and direction:
            - 'sea_ice_speed'      (float): geodesic speed (m s⁻¹);
                                            rounded to `speed_precision`
            - 'sea_ice_speed_kmdy' (float): geodesic speed (km day⁻¹);
                                            rounded to `speed_precision`
            - 'direction_of_sea_ice_displacement' (float): forward azimuth
                                            (degrees); rounded to
                                            `bearing_precision`
            - 'distance' (float): geodesic distance (m); rounded to
                                  `speed_precision`
            
        Sensor and scene identifiers:
            - 'scene_id' (str): Combination of 'File1' and 'File2' separated
                                by underscore
            - 'sensor1' (str):  Satellite identifier from File1
                                (prefix before first underscore)
            - 'sensor2' (str):  Satellite identifier from File2
 
    Notes:
        - SAR time fields `Time1_JS` and `Time2_JS` are seconds since
          2000-01-01 00:00:00.
        - A specific `pyproj` warning about database path setup is suppressed
          because it is expected in this runtime environment.
        - Required source columns: 'Time1_JS', 'Time2_JS', 'Lat1', 'Lon1',
          'Lat2', 'Lon2', 'File1', 'File2'. The columns 'Bear_deg',
          'Speed_kmdy', 'U_vel_ms', 'V_vel_ms', and 'Per_Valid' must also
          be present but are dropped after processing.
    """
    
    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta
    
    # The project database for pyproj is properly set by the code above
    # Okay to ignore this warning and only this warning
    import warnings
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        module="pyproj",
        message="pyproj unable to set database path"
    )
    
    
    # Read the SAR drift data file
    df = pd.read_csv(
        input_file, delimiter=config['delimiter'],
        header=0, engine='c', skiprows=skip_rows
    )
    df.columns = df.columns.str.strip()

    
    # Add the appropriate input file to a data frame
    # Julian seconds start from date 01-01-2000
    base_time = datetime(2000, 1, 1)

    # Create new Date* columnc by converting Time_JS* columns to datetime
    df['date_start'] = df["Time1_JS"].apply(
        lambda x: base_time + timedelta(seconds=x)
        )
    df['date_start'] = df['date_start'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df['date_end'] = df["Time2_JS"].apply(
        lambda x: base_time + timedelta(seconds=x)
        )
    df['date_end'] = df['date_end'].dt.strftime('%Y-%m-%d %H:%M:%S')
    

    # Calculate duration of observations in seconds
    df['duration_s'] = (
        df['Time2_JS'] - df['Time1_JS']
    )
    
    drift = _calculate_drift_daily(
        lat1=df['Lat1'].values,
        lon1=df['Lon1'].values,
        lat2=df['Lat2'].values,
        lon2=df['Lon2'].values,
        duration_s=df['duration_s'].values
    )
    
    df['Lat1'] = np.round(df['Lat1'], config['coordinate_precision'])
    df['Lon1'] = np.round(df['Lon1'], config['coordinate_precision'])
    df['Lat2'] = np.round(df['Lat2'], config['coordinate_precision'])
    df['Lon2'] = np.round(df['Lon2'], config['coordinate_precision'])
    df['X1'] = np.round(drift['X1'], config['coordinate_precision'])
    df['Y1'] = np.round(drift['Y1'], config['coordinate_precision'])
    df['X2'] = np.round(drift['X2'], config['coordinate_precision'])
    df['Y2'] = np.round(drift['Y2'], config['coordinate_precision'])
    df['sea_ice_x_displacement'] = np.round(
        drift['dx'], config['speed_precision']
    )
    df['sea_ice_y_displacement'] = np.round(
        drift['dy'], config['speed_precision']
    )
    df['u_ms'] = drift['u_ms']
    df['v_ms'] = drift['v_ms']
    df['sea_ice_speed'] = np.round(
        drift['speed_ms'],
        config['speed_precision']
    )
    df['sea_ice_speed_kmdy'] = np.round(
        drift['speed_kmdy'],
        config['speed_precision']
    )
    df['direction_of_sea_ice_displacement'] = np.round(
        drift['bearing'], config['bearing_precision']
    )
    df['distance'] = np.round(
        drift['distance'], config['speed_precision']
    )
    
    
    # identify satellites for analysis
    df['sensor1'] = df["File1"].str.partition("_")[0]
    df['sensor2'] = df["File2"].str.partition("_")[0]
    df['scene_id'] = df['File1'] + '_' + df['File2']
    
    df.rename(columns=
              {
                  'Lat1': 'latitude_1',
                  'Lon1': 'longitude_1',
                  'Lat2': 'latitude_2',
                  'Lon2': 'longitude_2'
        },
        inplace=True
    )

    
    df.drop(
        [
            'File1', 'File2', 'Time1_JS', 'Time2_JS',
            'U_vel_ms', 'V_vel_ms', 'Speed_kmdy', 'Bear_deg',
            'img1_mean', 'img1_std', 'img2_mean', 'img2_std',
            'img1s_mean', 'img1s_std', 'Per_Valid'
        ],
        axis=1,
        inplace=True
    )
    
    return df


def create_shape_package(df, gpkg_path, config):
    """
    Create a GeoPackage containing drift line vectors for SAR drift data.
 
    Builds LineString geometries from projected start and end coordinates
    (EPSG:3413) and writes all columns from the input DataFrame as a single
    `drift_lines` layer within a GeoPackage. A QML style file is embedded
    directly into the GeoPackage's `layer_styles` table for automatic styling
    when opened in QGIS.
 
    Args:
        df (pandas.DataFrame): Input DataFrame containing drift vectors, as
            produced by `read_sar_drift_data_file` and `outlier_search`.
            All columns are written to the GeoPackage. Expected columns
            include:
                Projected coordinates (EPSG:3413, metres):
                    - 'X1', 'Y1' (float): Start position.
                    - 'X2', 'Y2' (float): End position.
                Geographic coordinates (degrees):
                    - 'longitude_1', 'latitude_1' (float): Start lon/lat.
                    - 'longitude_2', 'latitude_2' (float): End lon/lat.
                Timestamps and duration:
                    - 'date_start' (str): Start datetime
                                         ('%Y-%m-%d %H:%M:%S').
                    - 'date_end'   (str): End datetime
                                         ('%Y-%m-%d %H:%M:%S').
                    - 'duration_s' (float): Observation duration (s).
                Sensor identifiers:
                    - 'sensor1', 'sensor2' (str): Satellite/sensor IDs.
                Science variables:
                    - 'sea_ice_x_displacement' (float): X displacement (m).
                    - 'sea_ice_y_displacement' (float): Y displacement (m).
                    - 'u_ms' (float): X velocity component (m s⁻¹).
                    - 'v_ms' (float): Y velocity component (m s⁻¹).
                    - 'sea_ice_speed' (float): Drift speed (m s⁻¹).
                    - 'sea_ice_speed_kmdy' (float): Drift speed (km day⁻¹).
                    - 'direction_of_sea_ice_displacement' (float): Forward
                                                                   azimuth
                                                                   (degrees).
                    - 'distance' (float): Geodesic displacement distance (m).
                Outlier flag (when present):
                    - 'outlier_category' (str): Two-digit outlier code;
                      included in the output if present in `df`.
        gpkg_path (str): Full path for the output GeoPackage file.
        config (dict): Configuration dictionary containing:
                - 'qml_file' (str): Path to the QML style file to embed.
 
    Returns:
        None
 
    Notes:
        - Geometry is a `LineString` from `(X1, Y1)` to `(X2, Y2)` in
          EPSG:3413 projected metres, not from geographic coordinates.
        - CRS is set to EPSG:3413 (NSIDC Sea Ice Polar Stereographic North).
        - A helper column `geometry_type` is added with the literal value
          `'line'` to identify the layer geometry type.
        - All columns present in `df` are written to the GeoPackage layer;
          no column filtering is applied.
        - The QML style is embedded via `_embed_qml_style`, so end users do
          not need the QML file present to load the styled layer in QGIS.
    """

    import logging
    import geopandas as gpd
    from shapely.geometry import LineString
    
    
    df_local = df.copy()
    df_local['geometry_line'] = df_local.apply(
        lambda row: LineString(
            [
                (row['X1'], row['Y1']),
                (row['X2'], row['Y2'])
            ]
        ),
        axis=1
    )
    
    
    # Create GeoDataFrame for lines (lines only)
    gdf_line = gpd.GeoDataFrame(
        df_local, geometry='geometry_line'
    )
    # Add a column to distinguish geometry type    
    gdf_line['geometry_type'] = 'line'  
    
   
    # Save as a single GeoPackage file (supports mixed geometries)
    gdf_line = gdf_line.rename(
        columns={'geometry_line': 'geometry'}
    ).set_geometry('geometry')
    gdf_line = gdf_line.set_crs('EPSG:3413')
    gdf_line.to_file(gpkg_path, layer='drift_lines', driver='GPKG')
    

    # embed .qml outlier layer style
    _embed_qml_style(gpkg_path, 'drift_lines', config['qml_file'])
    
    # log activity
    logger = logging.getLogger('sar_drift_ice_velocity_over_maosaic_vectors')
    logger.info(f'Created GeoPackage {gpkg_path}')
  
