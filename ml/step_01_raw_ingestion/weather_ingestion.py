"""
Weather Data Ingestion Module.
Fetches authentic atmospheric measurements from:
  - ECMWF ERA5 Reanalysis (historical / training periods)
  - ECMWF / GFS Operational Models (real-time live via Open-Meteo)

Supports configurable date ranges — no hardcoded year.
"""

import sys
import time
import requests
import pandas as pd
from pathlib import Path

# Ensure ML root is in path for direct execution
_ML_ROOT = Path(__file__).resolve().parent.parent
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

try:
    from .config import (
        VIDARBHA_STATIONS,
        WEATHER_RAW_DIR,
        TRAINING_START_DATE,
        TRAINING_END_DATE,
        WEATHER_HOURLY_VARS
    )
except (ImportError, ValueError):
    from step_01_raw_ingestion.config import (
        VIDARBHA_STATIONS,
        WEATHER_RAW_DIR,
        TRAINING_START_DATE,
        TRAINING_END_DATE,
        WEATHER_HOURLY_VARS
    )


class WeatherIngestion:
    """Ingests authentic hourly weather records from ECMWF ERA5 and operational models."""

    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout: int = 45, max_retries: int = 4):
        self.timeout = timeout
        self.max_retries = max_retries

    def fetch_station_historical(
        self,
        station_id: str,
        lat: float,
        lon: float,
        start_date: str = TRAINING_START_DATE,
        end_date: str = TRAINING_END_DATE
    ) -> pd.DataFrame:
        """
        Fetches ERA5 hourly historical weather reanalysis for a single station.

        Args:
            station_id: Identifier key from VIDARBHA_STATIONS.
            lat, lon: Geographic coordinates.
            start_date, end_date: ISO date strings defining the query window.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(WEATHER_HOURLY_VARS),
            "timezone": "Asia/Kolkata"
        }

        print(f"[Weather] Fetching ERA5 for {station_id} ({lat:.4f}, {lon:.4f}) [{start_date} → {end_date}]...")

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get(self.ARCHIVE_URL, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()

                if "hourly" not in data or "time" not in data["hourly"]:
                    raise ValueError(f"Invalid API response: {list(data.keys())}")

                df = pd.DataFrame(data["hourly"])
                df.rename(columns={"time": "timestamp"}, inplace=True)
                df["station_id"] = station_id
                df["latitude"] = lat
                df["longitude"] = lon
                df["timestamp"] = pd.to_datetime(df["timestamp"])

                print(f"[Weather] [OK] {station_id}: {len(df):,} records fetched.")
                return df

            except Exception as e:
                print(f"[Weather] Attempt {attempt}/{self.max_retries} failed for {station_id}: {e}")
                if attempt < self.max_retries:
                    time.sleep(2 * attempt)
                else:
                    raise RuntimeError(f"Failed to fetch weather for {station_id}: {e}")

    def fetch_live(self, lat: float, lon: float, station_id: str = "LIVE_NODE") -> pd.DataFrame:
        """Fetches real-time weather from ECMWF/GFS operational stream (last 48h + 24h forecast)."""
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
                resp = requests.get(self.FORECAST_URL, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()

                df = pd.DataFrame(data["hourly"])
                df.rename(columns={"time": "timestamp"}, inplace=True)
                df["station_id"] = station_id
                df["latitude"] = lat
                df["longitude"] = lon
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                return df
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(2)
                else:
                    raise RuntimeError(f"Failed to fetch live weather for ({lat}, {lon}): {e}")
    fetch_live_weather = fetch_live

    def collect_all_stations(
        self,
        start_date: str = TRAINING_START_DATE,
        end_date: str = TRAINING_END_DATE,
        output_dir: Path = WEATHER_RAW_DIR
    ) -> pd.DataFrame:
        """Downloads weather for all Vidarbha stations and saves per-station + combined CSVs."""
        output_dir.mkdir(parents=True, exist_ok=True)
        all_dfs = []

        for station_id, meta in VIDARBHA_STATIONS.items():
            df = self.fetch_station_historical(
                station_id=station_id,
                lat=meta["latitude"],
                lon=meta["longitude"],
                start_date=start_date,
                end_date=end_date
            )
            suffix = f"_{start_date[:4]}" if start_date != TRAINING_START_DATE else ""
            station_file = output_dir / f"weather_{station_id.lower()}{suffix}.csv"
            df.to_csv(station_file, index=False)
            all_dfs.append(df)
            time.sleep(1)

        combined = pd.concat(all_dfs, ignore_index=True)
        combined_file = output_dir / f"weather_vidarbha_combined_{start_date[:4]}.csv"
        combined.to_csv(combined_file, index=False)
        print(f"[Weather] [OK] Combined dataset: {combined_file} ({len(combined):,} rows)")
        return combined


if __name__ == "__main__":
    ingestor = WeatherIngestion()
    ingestor.collect_all_stations()
