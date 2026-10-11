"""
Air Quality (CAMS Satellite) Data Ingestion Module.
Fetches atmospheric pollutant measurements from Copernicus Atmosphere Monitoring Service (CAMS)
via the Open-Meteo Air Quality API.

Supports configurable date ranges — no hardcoded year.
NAQI computation delegated to the dedicated naqi.py module.
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
        AQ_RAW_DIR,
        TRAINING_START_DATE,
        TRAINING_END_DATE,
        AQ_HOURLY_VARS
    )
    from .naqi import compute_composite_naqi
except (ImportError, ValueError):
    from step_01_raw_ingestion.config import (
        VIDARBHA_STATIONS,
        AQ_RAW_DIR,
        TRAINING_START_DATE,
        TRAINING_END_DATE,
        AQ_HOURLY_VARS
    )
    from step_01_raw_ingestion.naqi import compute_composite_naqi


class AirQualityIngestion:
    """Ingests hourly CAMS satellite air quality measurements across the Vidarbha grid."""

    AQ_ARCHIVE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

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
        Fetches Copernicus CAMS reanalysis air quality for a single station.

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
            "hourly": ",".join(AQ_HOURLY_VARS),
            "timezone": "Asia/Kolkata"
        }

        print(f"[CAMS] Fetching for {station_id} ({lat:.4f}, {lon:.4f}) [{start_date} → {end_date}]...")

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get(self.AQ_ARCHIVE_URL, params=params, timeout=self.timeout)
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
                df["india_naqi"] = compute_composite_naqi(df)

                print(f"[CAMS] [OK] {station_id}: {len(df):,} records fetched.")
                return df

            except Exception as e:
                print(f"[CAMS] Attempt {attempt}/{self.max_retries} failed for {station_id}: {e}")
                if attempt < self.max_retries:
                    time.sleep(2 * attempt)
                else:
                    raise RuntimeError(f"Failed to fetch CAMS AQ for {station_id}: {e}")

    def fetch_live(self, lat: float, lon: float, station_id: str = "LIVE_NODE") -> pd.DataFrame:
        """Fetches real-time CAMS air quality (last 48h + 24h forecast)."""
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
                resp = requests.get(self.AQ_ARCHIVE_URL, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()

                df = pd.DataFrame(data["hourly"])
                df.rename(columns={"time": "timestamp"}, inplace=True)
                df["station_id"] = station_id
                df["latitude"] = lat
                df["longitude"] = lon
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df["india_naqi"] = compute_composite_naqi(df)
                return df
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(2)
                else:
                    raise RuntimeError(f"Failed to fetch live AQ for ({lat}, {lon}): {e}")
    fetch_live_aq = fetch_live

    def collect_all_stations(
        self,
        start_date: str = TRAINING_START_DATE,
        end_date: str = TRAINING_END_DATE,
        output_dir: Path = AQ_RAW_DIR
    ) -> pd.DataFrame:
        """Downloads CAMS AQ for all Vidarbha stations and saves per-station + combined CSVs."""
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
            station_file = output_dir / f"cams_{station_id.lower()}{suffix}.csv"
            df.to_csv(station_file, index=False)
            all_dfs.append(df)
            time.sleep(1)

        combined = pd.concat(all_dfs, ignore_index=True)
        combined_file = output_dir / f"cams_vidarbha_combined_{start_date[:4]}.csv"
        combined.to_csv(combined_file, index=False)
        print(f"[CAMS] [OK] Combined dataset: {combined_file} ({len(combined):,} rows)")
        return combined


if __name__ == "__main__":
    ingestor = AirQualityIngestion()
    ingestor.collect_all_stations()
