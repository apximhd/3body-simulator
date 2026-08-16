"""
Physical constants and units.
Unit system:
  - Mass   : solar masses (Msun)
  - Length : astronomical units (AU)
  - Time   : 1 year = 2π (Earth's angular frequency)
In these units G = 1.
"""

import numpy as np

# 1 AU in km
AU_KM = 149597870.7

# 1 km in AU
KM = 1.0 / AU_KM

# Time unit: 1 year = 2π
YEAR = 2.0 * np.pi

# 1 km/s in AU / (time unit)
KMS = 1.0 / 29.7859

# degree in radians
DEG = np.pi / 180.0

# Masses (for reference)
M_EARTH = 6.0e24 / (2.0e30)   # ~ 3e-6 Msun
M_MOON = 7.35e22 / (2.0e30)
