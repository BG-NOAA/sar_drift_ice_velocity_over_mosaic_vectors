# -*- coding: utf-8 -*-
"""
******************************************************************************
 Project:     SAR Drift Ice Velocity over MOSAiC Vectors
 Purpose:     Versioned algorithm parameters for the SAR drift processing
              pipeline. Centralizing constants here ensures any changes to
              rounding precision are tracked under version control.
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

"""
Versioned algorithm parameters:
BEARING_PRECISION       (int):   Number of decimal places to retain
                                 in Bear_deg.
SPEED_PRECISION         (int):   Number of decimal places to retain
                                 in Speed_kmdy.
DISPLACEMENT_PRECISION  (int):   Number of decimal places to retain
                                 in displacement variables like U, V or dx, dy.
COORDINATE_PRECISION    (int):   Number of decimal places to retain
                                 when transforming X, Y coordinates in meters
                                 from longitude, latitude in degrees.
"""

# Rounding
BEARING_PRECISION = 0
SPEED_PRECISION = 3
DISPLACEMENT_PRECISION = 4
COORDINATE_PRECISION = 4