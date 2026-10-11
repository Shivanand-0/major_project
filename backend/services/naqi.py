"""
India National Air Quality Index (NAQI) Computation Module.
Implements official CPCB (Central Pollution Control Board) breakpoint tables
and sub-index linear interpolation for all 6 criteria pollutants.

References:
  - CPCB National Air Quality Index (2014) Technical Document
  - Breakpoint concentrations aligned with 24-hr / 8-hr averaging windows
"""

import numpy as np
import pandas as pd


# Official CPCB Breakpoints: (C_lo, C_hi, I_lo, I_hi)
CPCB_BREAKPOINTS = {
    "pm2_5": [
        (0, 30, 0, 50), (30, 60, 51, 100), (60, 90, 101, 200),
        (90, 120, 201, 300), (120, 250, 301, 400), (250, 380, 401, 500)
    ],
    "pm10": [
        (0, 50, 0, 50), (50, 100, 51, 100), (100, 250, 101, 200),
        (250, 350, 201, 300), (350, 430, 301, 400), (430, 510, 401, 500)
    ],
    "nitrogen_dioxide": [
        (0, 40, 0, 50), (40, 80, 51, 100), (80, 180, 101, 200),
        (180, 280, 201, 300), (280, 400, 301, 400), (400, 500, 401, 500)
    ],
    "sulphur_dioxide": [
        (0, 40, 0, 50), (40, 80, 51, 100), (80, 380, 101, 200),
        (380, 800, 201, 300), (800, 1600, 301, 400), (1600, 2000, 401, 500)
    ],
    "carbon_monoxide": [
        (0, 1.0, 0, 50), (1.0, 2.0, 51, 100), (2.0, 10.0, 101, 200),
        (10.0, 17.0, 201, 300), (17.0, 34.0, 301, 400), (34.0, 50.0, 401, 500)
    ],
    "ozone": [
        (0, 50, 0, 50), (50, 100, 51, 100), (100, 168, 101, 200),
        (168, 208, 201, 300), (208, 748, 301, 400), (748, 1000, 401, 500)
    ],
}

# The 6 criteria pollutants in standard column naming
CRITERIA_POLLUTANTS = ["pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide", "carbon_monoxide", "ozone"]


def compute_subindex(concentration: float, pollutant: str) -> float:
    """
    Computes the CPCB linear interpolation sub-index for a single
    pollutant concentration value.

    Args:
        concentration: Measured pollutant concentration (µg/m³, mg/m³ for CO).
        pollutant: Standard column name (e.g. 'pm2_5', 'nitrogen_dioxide').

    Returns:
        Sub-index value (0–500), or NaN if invalid.
    """
    if pd.isna(concentration) or concentration < 0:
        return np.nan

    bp_list = CPCB_BREAKPOINTS.get(pollutant)
    if not bp_list:
        return np.nan

    # CAMS reports CO in µg/m³; CPCB breakpoints use mg/m³
    if pollutant == "carbon_monoxide" and concentration > 50:
        concentration = concentration / 1000.0

    for c_lo, c_hi, i_lo, i_hi in bp_list:
        if c_lo <= concentration <= c_hi:
            return i_lo + ((i_hi - i_lo) / (c_hi - c_lo)) * (concentration - c_lo)

    # Beyond highest breakpoint → cap at 500
    if concentration > bp_list[-1][1]:
        return 500.0

    return np.nan


def compute_composite_naqi(df: pd.DataFrame) -> pd.Series:
    """
    Computes the official CPCB India NAQI composite index for a DataFrame.

    NAQI = max(SubIndex_PM2.5, SubIndex_PM10, SubIndex_NO2, SubIndex_SO2, SubIndex_CO, SubIndex_O3)

    Args:
        df: DataFrame containing pollutant columns matching CRITERIA_POLLUTANTS.

    Returns:
        Series of composite NAQI values rounded to 1 decimal place.
    """
    subindex_series = []
    for pol in CRITERIA_POLLUTANTS:
        if pol in df.columns:
            sub = df[pol].apply(lambda v: compute_subindex(v, pol))
            subindex_series.append(sub)

    if not subindex_series:
        return pd.Series(np.nan, index=df.index)

    stacked = pd.concat(subindex_series, axis=1)
    return stacked.max(axis=1).round(1)


def get_naqi_category(aqi_val: float) -> str:
    """
    Returns the official CPCB health category string for a given AQI value.

    Categories: Good (0-50), Satisfactory (51-100), Moderate (101-200),
                Poor (201-300), Very Poor (301-400), Severe (401-500).
    """
    if pd.isna(aqi_val):
        return "Unknown"
    if aqi_val <= 50:
        return "Good"
    elif aqi_val <= 100:
        return "Satisfactory"
    elif aqi_val <= 200:
        return "Moderate"
    elif aqi_val <= 300:
        return "Poor"
    elif aqi_val <= 400:
        return "Very Poor"
    else:
        return "Severe"
