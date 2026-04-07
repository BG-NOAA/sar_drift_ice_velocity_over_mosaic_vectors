# -*- coding: utf-8 -*-
"""
******************************************************************************

 Project:     SAR Drift Ice Velocity over MOSAiC Vectors
 Purpose:     For each MOSAiC buoy, filter SAR-derived sea-ice drift
              observations, reproject coordinates to a configurable EPSG,
              compute drift kinematics, and write per-buoy CSVs and
              QGIS-styled GeoPackages for comparison with buoy observations.
 Author:      Brendon Gory, brendon.gory@noaa.gov
                            brendon.gory@colostate.edu
              Data Science Application Specialist (Research Associate II)
              at CSU CIRA
 Supervisors: Dr. Ludovic Brucker, ludovic.brucker@noaa.gov
              NESDIS Physical Scientist
              Dr. Prasanjit Dash, prasanjit.dash@noaa.gov
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


def setup_logger(config):
    """
    Configure and return a file-based logger for the SAR drift converter run.

    Creates a timestamped log file in the specified output directory and
    attaches a file handler to the 'sar_drift_converter' logger. Each run
    produces a uniquely named log file based on the UTC time at invocation.

    Args:
        output_dir (str): Directory where the log file will be written.
                          Must exist prior to calling this function.

    Returns:
        tuple:
            - logger (logging.Logger): Configured logger instance named
              'sar_drift_converter', set to INFO level. Retrieve in any
              module via `logging.getLogger('sar_drift_converter')`.
            - log_path (str): Full path to the log file created, formatted
              as `<output_dir>/run_YYYYMMDD_HHMMSS.log` in UTC.

    Notes:
        - Log records follow the format:
          `YYYY-MM-DD HH:MM:SS,mmm | LEVEL | message`
        - The logger is retrieved by name, so subsequent calls with the same
          process will return the same logger instance and append an
          additional file handler. This function should only be called once
          per run.
        - Only a file handler is attached; no console (stream) handler is
          added, so log output will not appear in stdout unless a handler is
          added separately elsewhere.
    """
    
    import os
    import logging
    from datetime import datetime
    
    log_path = os.path.join(
        config['log_dir'],
        f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.log"
    )
    logger = logging.getLogger('sar_drift_ice_velocity_over_maosaic_vectors')
    logger.setLevel(logging.INFO)

    # file handler
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.INFO)


    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    fh.setFormatter(formatter)

    logger.addHandler(fh)

    return logger, log_path


def read_json_config():
    """
    Parse and validate configuration for the SAR Drift Ice Velocity over
    MOSAiC Vectors pipeline.

    Reads a JSON config file specified via the `-c` / `--config_file`
    command-line argument and validates its contents against a strict schema.
    Ensures all required paths exist, validates types for each parameter,
    creates output subdirectories, and injects versioned algorithm precision
    constants from `constants.py`.

    Expected JSON keys (must match exactly):
        - "sar_drift_directory"     (str):  Path to directory containing SAR
                                            drift delimited files for batch
                                            processing.
        - "qml_file"                (str):  Path to QML file that applies a
                                            style to GeoPackages when opened
                                            in QGIS.
        - "epsg"                    (int):  EPSG code of the target projected
                                            CRS. Must be 3413 (NSIDC Sea Ice
                                            Polar Stereographic North) or 6931
                                            (EASE-Grid 2.0 North).
        - "clear_output_dir"        (bool): Remove output subdirectories and
                                            all contents from previous runs
                                            before processing.
        - "delimiter"               (str):  Field separator in the input files
                                            (e.g., ",", "\\t").
        - "skip_rows_before_header" (int):  Number of rows to skip before the
                                            header row in each data file.
        - "verbose"                 (bool): Print resolved configuration
                                            parameters to the console.
        - "version"                 (str):  Version string appended to all
                                            output filenames (e.g., "01").

    Command-line arguments:
        -c, --config_file: Path to a JSON file with all required configuration.

    Returns:
        dict: Validated configuration dictionary containing all JSON parameters
              (with paths normalized and EPSG validated), versioned algorithm
              precision constants from `constants.py`, and the following
              resolved output subdirectory paths:
              - 'log_dir':  log/
              - 'csv_dir':  csv/
              - 'gpkg_dir': gpkg/

    Raises:
        Exits the script (status code 1) if:
            - The config file argument is missing or the file cannot be opened.
            - Required keys are absent or unexpected keys are present.
            - Parameter types are invalid (e.g., non-bool for clear_output_dir).
            - `epsg` is not 3413 or 6931.
            - Required paths (`sar_drift_directory`, `qml_file`) do not exist.

    Example:
        $ python sar_drift_ice_velocity_over_mosaic_vectors.py -c config.json
    """

    import util
    import argparse
    import os
    import shutil
    import json
    from constants import (
        BEARING_PRECISION,
        SPEED_PRECISION,
        DISPLACEMENT_PRECISION,
        COORDINATE_PRECISION
    )


    parser = argparse.ArgumentParser(description=(
        'Reformats SAR drift data to CSV and GeoPackage files.'
        )
    )
    parser.add_argument('-c', '--config_file', type=str, action='store',
                        help='Path to config JSON file')
    args = parser.parse_args()
    if not args.config_file:
        util.error_msg('Missing or empty config file argument')

    config_file = os.path.normpath(args.config_file)
    with open(config_file, 'r') as f:
        config = json.load(f)


    # Key validation
    required_json_keys = {
        "sar_drift_directory", "qml_file", "clear_output_dir", "epsg",
        "delimiter", "skip_rows_before_header", "verbose", 'version'
    }
    config_keys = set(config.keys())
    missing = required_json_keys - config_keys
    extra   = config_keys - required_json_keys
    if missing:
        util.error_msg(
            f"Missing required keys in {config_file}: {', '.join(missing)}"
        )
    if extra:
        util.error_msg(
            f"Unexpected keys in {config_file}: {', '.join(extra)}"
        )


    # define schema
    # (key, expected_type, min_value_or_None, allow_zero)    
    schema = [
        ("clear_output_dir",          bool,  None, None),
        ("verbose",                   bool,  None, None),
        ("skip_rows_before_header",   int,   0,    True),
    ]

    for key, expected_type, min_val, allow_zero in schema:
        val = config[key]
        if not isinstance(val, expected_type):
            util.error_msg(
                f'`{key}` must be {expected_type.__name__}, '
                f'got {type(val).__name__}'
            )
        if min_val is not None and val < min_val:
            util.error_msg(f'`{key} = {val}` must be >= {min_val}')
        config[key] = expected_type(val)


    # epsg validation
    if config['epsg'] not in [3413, 6931]:
        util.error_msg('`epsg` must be `3413` or `6931`')
        
        
    # Path resolution and existence checks
    path_checks = [
        ('sar_drift_directory', 'sar_drift_directory', True),
        ('qml_file', 'qml_file', True)
    ]
    resolved_paths = {}
    for json_key, config_key, must_exist in path_checks:
        path = os.path.normpath(config[json_key])
        if must_exist and not os.path.exists(path):
            util.error_msg(f"Cannot find `{config_key}`: `{path}`")
        resolved_paths[config_key] = path

    
    # Output directory setup
    subdirs = ['log', 'csv', 'gpkg']        
    subdir_paths = {}
    for name in subdirs:
        path = os.path.normpath(name)
        if os.path.exists(path) and config['clear_output_dir']:
            print(f"Clearing output directory --> {path}")
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)
        subdir_paths[f'{name}_dir'] = path

    
    # Delimiter decode (\t etc.)
    delimiter = config['delimiter'].encode().decode('unicode_escape')

    
    # Build final config
    config = {
        **resolved_paths,
        **subdir_paths,
        'clear_output_dir':        config['clear_output_dir'],
        'epsg':                    config['epsg'],
        'delimiter':               delimiter,
        'skip_rows_before_header': config['skip_rows_before_header'],
        'bearing_precision':       BEARING_PRECISION,
        'speed_precision':         SPEED_PRECISION,
        'displacement_precision':  DISPLACEMENT_PRECISION,
        'coordinate_precision':    COORDINATE_PRECISION,
        'verbose':                 config['verbose'],
        'version':                 config['version']
    }

    
    # echo
    if config['verbose']:
        labels = {
            'sar_drift_directory':    'sar drift directory',
            'qml_file':               'qml file',
            'clear_output_dir':       'clear output dir',
            'epsg':                   'epsg',
            'delimiter':              'delimiter',
            'skip_rows_before_header':'skip rows before header',
            'bearing_precision':      'bearing precision',
            'speed_precision':        'speed precision',
            'displacement_precision': 'displacement precision',
            'coordinate_precision': 'coordinate precision'
        }
        lines = ["CONF PARAMS:"]
        for key, label in labels.items():
            lines.append(f"  {label:<25} {config[key]}")
        print('\n'.join(lines))

    return config


def main():
    """
    Main execution workflow for the SAR Drift Ice Velocity over MOSAiC
    Vectors pipeline.

    This function orchestrates the full per-buoy processing loop:
        1. Parses and validates configuration via `read_json_config`.
        2. Discovers all .txt and .csv files in `sar_drift_directory`.
        3. Initializes a timestamped log file.
        4. For each buoy file:
               a. Reads and preprocesses the SAR drift data.
               b. Applies bearing/speed validity, speed ceiling, and
                  correlation quality filters.
               c. Writes a filtered, reduced-column CSV.
               d. Writes a drift-line GeoPackage in the configured EPSG
                  with an embedded QGIS style.
        5. Logs total elapsed time on completion.

    Intended to be called only when the script is run as a standalone
    program (i.e. via `if __name__ == "__main__"`).
    """

    import pyproj_setup
    import util
    import os
    from datetime import datetime
    from glob import glob
    from tqdm import tqdm
    
    
    run_start = datetime.utcnow()
    
    # parse user arguments
    config = read_json_config()

    

    # find files to process
    files= []
    all_files = glob(os.path.join(config['sar_drift_directory'], '*'))
    for file in all_files:
        if ('.txt' in file) or ('.csv' in file):
            files.append(file)
        
        
    # initialize logger
    logger, log_path = setup_logger(config)
    logger.info(
        f"Run started | {run_start}"
    )
    logger.info(f"Input directory: {config['sar_drift_directory']}")
    logger.info(f"Found {len(files)} candidate files")
        
    
    # read all files into one DataFrame
    for gfilter_path in tqdm(files, "Reading gfilter files..."):    
        basename = os.path.basename(gfilter_path)
        buoy_id = basename.split('_')[0]
    
        df = util.read_sar_drift_data_file(
            input_file=gfilter_path,
            config=config,
            skip_rows=config['skip_rows_before_header']
        )
        logger.info(
            f"{basename} | initial row size: {df.shape[0]}"
        )
    
        # remove invalid bearings and speeds
        initial_row_size = df.shape[0]
        df = df[
            (df['direction_of_sea_ice_displacement'] != 0) &
            (df['sea_ice_speed'] > 0)
        ]
        if initial_row_size != df.shape[0]:
            logger.info(
                f"{basename} | after bearing/speed validity: "
                f"{df.shape[0]} (dropped "
                f"{initial_row_size - df.shape[0]})"
            )

        # remove invalid speeds
        initial_row_size = df.shape[0]
        df = df[df['sea_ice_speed'] < 25.0]
        if initial_row_size != df.shape[0]:
            logger.info(
                f"{basename} | after speed filter "
                f"(sea_ice_speed >= 25.0): {df.shape[0]} "
                f"(dropped {initial_row_size - df.shape[0]})"
            )

        # remove rows where MaxCorr2 <= MaxCorr1
        initial_row_size = df.shape[0]
        df = df[df['Maxcorr2'] > df['Maxcorr1']]
        if initial_row_size != df.shape[0]:
            logger.info(
                f"{basename} | after Maxcorr2 > Maxcorr1: "
                f"{df.shape[0]} (dropped "
                f"{initial_row_size - df.shape[0]})"
            )


        # drop Maxcorr columns
        df.drop(['Maxcorr1', 'Maxcorr2'], axis=1, inplace=True)
        
        
        # create reduced GeoPackage
        gpkg_path = os.path.join(
            config['gpkg_dir'],
            f'NOAA_SIVelocity_SAR_{buoy_id}__{config["epsg"]}_'
            f'v{config["version"]}.gpkg'
        )
        util.create_shape_package(df, gpkg_path, config)
        
        
        # drop geod distance
        df.drop('distance_geod', axis=1, inplace=True)
        
        # create reduced CSV file
        csv_path = os.path.join(
            config['csv_dir'],
            f'NOAA_SIVelocity_SAR_{buoy_id}__{config["epsg"]}_'
            f'v{config["version"]}.csv'
        )
        df.to_csv(csv_path, index=False)
        logger.info(f'Created CSV {csv_path}')

    
    run_end = datetime.utcnow() 
    elapsed = run_end - run_start
    logger.info(
        f"Run complete | {run_end} | elapsed={elapsed}"
    )
    
    
if __name__ == "__main__":
    main()