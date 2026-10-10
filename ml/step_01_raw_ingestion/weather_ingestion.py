"""
Authentic Weather Data Ingestion Module.
Fetches real atmospheric measurements from ECMWF ERA5 / ERA5-Land Reanalysis (Historical)
and ECMWF/GFS Operational Weather Models (Real-time Live) via Open-Meteo.
No synthetic generation used.
"""

import time
import requests
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List

try:
    from .config import (
        VIDARBHA_STATIONS,
        WEATHER_RAW_DIR,
        HISTORICAL_START_DATE,
        HISTORICAL_END_DATE,
        WEATHER_HOURLY_VARS
    )
except ImportError:
    from config import (
        VIDARBHA_STATIONS,
        WEATHER_RAW_DIR,
        HISTORICAL_START_DATE,
        HISTORICAL_END_DATE,
        WEATHER_HOURLY_VARS
    )


class AuthenticWeatherIngestion:
    """Ingests authentic hourly weather records from ECMWF ERA5 Reanalysis and Operational Models."""

    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout: int = 45, max_retries: int = 4):
        self.timeout = timeout
        self.max_retries = max_retries

    def fetch_historical_station_weather(
        self,
        station_id: str,
        lat: float,
        lon: float,
        start_date: str = HISTORICAL_START_DATE,
        end_date: str = HISTORICAL_END_DATE
    ) -> pd.DataFrame:
        """
        Queries authentic ECMWF ERA5 hourly historical weather reanalysis for specific coordinates.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(WEATHER_HOURLY_VARS),
            "timezone": "Asia/Kolkata"
        }

        print(f"[Weather Ingestion] Fetching authentic ERA5 weather for {station_id} ({lat:.4f}, {lon:.4f}) [{start_date} to {end_date}]...")

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(self.ARCHIVE_URL, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                if "hourly" not in data or "time" not in data["hourly"]:
                    raise ValueError(f"Invalid API response payload structure: {data}")

                df = pd.DataFrame(data["hourly"])
                df.rename(columns={"time": "timestamp"}, inplace=True)
                df["station_id"] = station_id
                df["latitude"] = lat
                df["longitude"] = lon
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df["data_source"] = "ECMWF_ERA5_Reanalysis"

                print(f"[Weather Ingestion] Successfully fetched {len(df):,} authentic records for {station_id}.")
                return df

            except Exception as e:
                print(f"[Weather Ingestion] Attempt {attempt}/{self.max_retries} failed for {station_id}: {e}")
                if attempt < self.max_retries:
                    time.sleep(2 * attempt)
                else:
                    raise RuntimeError(f"Failed to fetch authentic weather data for {station_id} after {self.max_retries} retries: {e}")

    def fetch_live_weather(self, lat: float, lon: float, station_id: str = "LIVE_NODE") -> pd.DataFrame:
        """
        Fetches authentic live real-time meteorology and 24-hr historical context.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(WEATHER_HOURLY_VARS),
            "past_days": 2,
            "forecast_days": 1,
            "timezone": "Asia/Kolkata"
        }
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(self.FORECAST_URL, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                df = pd.DataFrame(data["hourly"])
                df.rename(columns={"time": "timestamp"}, inplace=True)
                df["station_id"] = station_id
                df["latitude"] = lat
                df["longitude"] = lon
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df["data_source"] = "OpenMeteo_Operational_Live"
                return df
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(2)
                else:
                    raise RuntimeError(f"Failed to fetch live weather for ({lat}, {lon}): {e}")

    def collect_all_historical_stations(self, output_dir: Path = WEATHER_RAW_DIR) -> pd.DataFrame:
        """Downloads authentic weather data for all Vidarbha stations and saves to CSV."""
        output_dir.mkdir(parents=True, exist_ok=True)
        all_dfs = []

        for station_id, meta in VIDARBHA_STATIONS.items():
            df = self.fetch_historical_station_weather(
                station_id=station_id,
                lat=meta["latitude"],
                lon=meta["longitude"]
            )
            station_file = output_dir / f"weather_{station_id.lower()}.csv"
            df.to_csv(station_file, index=False)
            all_dfs.append(df)
            time.sleep(1)  # Respect rate limits

        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_file = output_dir / "weather_vidarbha_combined.csv"
        combined_df.to_csv(combined_file, index=False)
        print(f"[SUCCESS] Saved combined authentic weather dataset: {combined_file} ({len(combined_df):,} rows)")
        return combined_df


if __name__ == "__main__":
    ingestor = AuthenticWeatherIngestion()
    combined = ingestor.collect_all_historical_stations()
    print("Sample Records:\n", combined.head(3))
