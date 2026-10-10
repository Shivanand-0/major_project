"""
Authentic Air Quality Data Ingestion Module.
Fetches real atmospheric pollutant measurements from Copernicus Atmosphere Monitoring Service (CAMS)
and computes official Indian National Air Quality Index (India NAQI) from raw pollutant concentrations.
No synthetic generation used.
"""

import time
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from .config import (
        VIDARBHA_STATIONS,
        AQ_RAW_DIR,
        HISTORICAL_START_DATE,
        HISTORICAL_END_DATE,
        AQ_HOURLY_VARS
    )
except ImportError:
    from config import (
        VIDARBHA_STATIONS,
        AQ_RAW_DIR,
        HISTORICAL_START_DATE,
        HISTORICAL_END_DATE,
        AQ_HOURLY_VARS
    )


# Official CPCB Breakpoints: (C_lo, C_hi, I_lo, I_hi)
CPCB_BREAKPOINTS = {
    "pm2_5": [(0, 30, 0, 50), (30, 60, 51, 100), (60, 90, 101, 200), (90, 120, 201, 300), (120, 250, 301, 400), (250, 380, 401, 500)],
    "pm10":  [(0, 50, 0, 50), (50, 100, 51, 100), (100, 250, 101, 200), (250, 350, 201, 300), (350, 430, 301, 400), (430, 510, 401, 500)],
    "nitrogen_dioxide": [(0, 40, 0, 50), (40, 80, 51, 100), (80, 180, 101, 200), (180, 280, 201, 300), (280, 400, 301, 400), (400, 500, 401, 500)],
    "sulphur_dioxide":  [(0, 40, 0, 50), (40, 80, 51, 100), (80, 380, 101, 200), (380, 800, 201, 300), (800, 1600, 301, 400), (1600, 2000, 401, 500)],
    "carbon_monoxide":  [(0, 1.0, 0, 50), (1.0, 2.0, 51, 100), (2.0, 10.0, 101, 200), (10.0, 17.0, 201, 300), (17.0, 34.0, 301, 400), (34.0, 50.0, 401, 500)],
    "ozone":            [(0, 50, 0, 50), (50, 100, 51, 100), (100, 168, 101, 200), (168, 208, 201, 300), (208, 748, 301, 400), (748, 1000, 401, 500)],
}

def _calc_subindex_scalar(conc: float, pollutant: str) -> float:
    """Computes linear interpolation sub-index for a single pollutant concentration."""
    if pd.isna(conc) or conc < 0:
        return np.nan
    bp_list = CPCB_BREAKPOINTS.get(pollutant)
    if not bp_list:
        return np.nan
    # Adjust CO from µg/m³ to mg/m³ if needed
    if pollutant == "carbon_monoxide" and conc > 50:
        conc = conc / 1000.0
    for c_lo, c_hi, i_lo, i_hi in bp_list:
        if c_lo <= conc <= c_hi:
            return i_lo + ((i_hi - i_lo) / (c_hi - c_lo)) * (conc - c_lo)
    max_c_lo, max_c_hi, max_i_lo, max_i_hi = bp_list[-1]
    if conc > max_c_hi:
        return 500.0
    return np.nan

def compute_cpcb_composite_naqi(df: pd.DataFrame) -> pd.Series:
    """
    Computes official Central Pollution Control Board (CPCB) India NAQI composite index.
    In accordance with CPCB standards:
      NAQI = max(SubIndex_PM2.5, SubIndex_PM10, SubIndex_NO2, SubIndex_SO2, SubIndex_CO, SubIndex_O3)
    """
    subindex_dfs = []
    for pol in ["pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide", "carbon_monoxide", "ozone"]:
        if pol in df.columns:
            sub = df[pol].apply(lambda v: _calc_subindex_scalar(v, pol))
            subindex_dfs.append(sub)
    
    if not subindex_dfs:
        return pd.Series(np.nan, index=df.index)
    
    stacked = pd.concat(subindex_dfs, axis=1)
    return stacked.max(axis=1).round(1)


def get_naqi_category(aqi_val: float) -> str:
    """Returns official CPCB category for an AQI value."""
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


class AuthenticAirQualityIngestion:
    """Ingests authentic hourly air quality measurements across the Vidarbha monitoring grid."""

    AQ_ARCHIVE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    def __init__(self, timeout: int = 45, max_retries: int = 4):
        self.timeout = timeout
        self.max_retries = max_retries

    def fetch_historical_station_aq(
        self,
        station_id: str,
        lat: float,
        lon: float,
        start_date: str = HISTORICAL_START_DATE,
        end_date: str = HISTORICAL_END_DATE
    ) -> pd.DataFrame:
        """
        Fetches authentic Copernicus Atmosphere Monitoring Service (CAMS) reanalysis measurements.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(AQ_HOURLY_VARS),
            "timezone": "Asia/Kolkata"
        }

        print(f"[AQ Ingestion] Fetching authentic CAMS air quality for {station_id} ({lat:.4f}, {lon:.4f}) [{start_date} to {end_date}]...")

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(self.AQ_ARCHIVE_URL, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                if "hourly" not in data or "time" not in data["hourly"]:
                    raise ValueError(f"Invalid API response structure: {data}")

                df = pd.DataFrame(data["hourly"])
                df.rename(columns={"time": "timestamp"}, inplace=True)
                df["station_id"] = station_id
                df["latitude"] = lat
                df["longitude"] = lon
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df["india_naqi"] = compute_cpcb_composite_naqi(df)
                df["data_source"] = "Copernicus_CAMS_Atmospheric_Reanalysis"

                print(f"[AQ Ingestion] Successfully fetched {len(df):,} authentic AQ records for {station_id}.")
                return df

            except Exception as e:
                print(f"[AQ Ingestion] Attempt {attempt}/{self.max_retries} failed for {station_id}: {e}")
                if attempt < self.max_retries:
                    time.sleep(2 * attempt)
                else:
                    raise RuntimeError(f"Failed to fetch authentic AQ data for {station_id} after {self.max_retries} retries: {e}")

    def fetch_live_aq(self, lat: float, lon: float, station_id: str = "LIVE_NODE") -> pd.DataFrame:
        """
        Fetches authentic live air quality from Copernicus operational stream.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(AQ_HOURLY_VARS) + ",us_aqi,european_aqi",
            "past_days": 2,
            "forecast_days": 1,
            "timezone": "Asia/Kolkata"
        }
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(self.AQ_ARCHIVE_URL, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                df = pd.DataFrame(data["hourly"])
                df.rename(columns={"time": "timestamp"}, inplace=True)
                df["station_id"] = station_id
                df["latitude"] = lat
                df["longitude"] = lon
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df["india_naqi"] = compute_cpcb_composite_naqi(df)
                df["data_source"] = "Copernicus_CAMS_Operational_Live"
                return df
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(2)
                else:
                    raise RuntimeError(f"Failed to fetch live AQ for ({lat}, {lon}): {e}")

    def collect_all_historical_stations(self, output_dir: Path = AQ_RAW_DIR) -> pd.DataFrame:
        """Downloads authentic air quality data for all Vidarbha stations and saves to CSV."""
        output_dir.mkdir(parents=True, exist_ok=True)
        all_dfs = []

        for station_id, meta in VIDARBHA_STATIONS.items():
            df = self.fetch_historical_station_aq(
                station_id=station_id,
                lat=meta["latitude"],
                lon=meta["longitude"]
            )
            station_file = output_dir / f"air_quality_{station_id.lower()}.csv"
            df.to_csv(station_file, index=False)
            all_dfs.append(df)
            time.sleep(1)

        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_file = output_dir / "air_quality_vidarbha_combined.csv"
        combined_df.to_csv(combined_file, index=False)
        print(f"[SUCCESS] Saved combined authentic AQ dataset: {combined_file} ({len(combined_df):,} rows)")
        return combined_df


if __name__ == "__main__":
    ingestor = AuthenticAirQualityIngestion()
    live = ingestor.fetch_live_aq(lat=21.1458, lon=79.0882)
    print("Live CAMS Air Quality for Nagpur (Recent 3 hours):")
    print(live.tail(3)[["timestamp", "pm2_5", "pm10", "nitrogen_dioxide", "india_naqi", "us_aqi"]])
