# -*- coding: utf-8 -*-
"""
******************************************************************************

 Project:     SAR Drift COnverter
 Purpose:     Standalone script that configures the PROJ data directory for
              pyproj by deriving paths from the active Conda environment.
              Sets PROJ_DATA and PROJ_LIB environment variables and calls
              set_data_dir() before any pyproj-dependent library is imported.
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

import os
import sys
import warnings
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
with warnings.catch_warnings():
    warnings.simplefilter("ignore", UserWarning)
    from pyproj.datadir import set_data_dir
    set_data_dir(str(proj_dir))
    import pyproj