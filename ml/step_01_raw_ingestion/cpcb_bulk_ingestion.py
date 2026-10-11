"""
Bulk CPCB Ground Station Data Ingestion from OpenAQ Public S3 Archive.
Downloads continuous physical analyzer readings (PM2.5, PM10, NO2, SO2, CO, O3)
recorded by CPCB / MPCB CAAQMS stations via the OpenAQ public data archive.

This module handles HISTORICAL / BULK data downloads.
For live real-time CPCB readings, use cpcb_ground_truth.py.
"""

import gzip
import io
import time
import requests
import pandas as pd
import sys
import numpy as np
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET

# Ensure ML root is in path for direct execution
_ML_ROOT = Path(__file__).resolve().parent.parent
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

try:
    from .config import CPCB_RAW_DIR
    from .naqi import compute_composite_naqi
except (ImportError, ValueError):
    from step_01_raw_ingestion.config import CPCB_RAW_DIR
    from step_01_raw_ingestion.naqi import compute_composite_naqi

S3_BASE_URL = "https://openaq-data-archive.s3.amazonaws.com"
S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

# Physical CPCB / MPCB Station Registry on OpenAQ
OPENAQ_STATIONS = {
    "NAGPUR_CENTRAL": {
        "location_id": 5621,
        "name": "Nagpur Central - Civil Lines (CPCB/MPCB)",
        "latitude": 21.152875,
        "longitude": 79.051753
    },
    "CHANDRAPUR_MIDC": {
        "location_id": 5565,
        "name": "Chandrapur - MIDC Khutala (CPCB/MPCB)",
        "latitude": 19.977530,
        "longitude": 79.233709
    },
    "AMRAVATI_CENTRAL": {
        "location_id": 3409458,
        "name": "Amravati - Shivneri Colony (CPCB/MPCB)",
        "latitude": 20.940236,
        "longitude": 77.789525
    },
    "AKOLA_WEST": {
        "location_id": 3409456,
        "name": "Akola - Ramdaspeth (CPCB/MPCB)",
        "latitude": 20.719516,
        "longitude": 77.000253
    }
}

# Parameter normalization: OpenAQ column names → standard analytical schema
PARAM_MAP = {
    "pm25": "pm2_5",
    "pm10": "pm10",
    "no2": "nitrogen_dioxide",
    "so2": "sulphur_dioxide",
    "co": "carbon_monoxide",
    "o3": "ozone"
}


class CpcbBulkIngestion:
    """Downloads authentic physical CPCB monitoring data from OpenAQ S3 archive."""

    def __init__(self, max_workers: int = 12):
        self.max_workers = max_workers
        self.session = requests.Session()

    def _list_s3_keys(self, location_id: int, year: int) -> List[str]:
        """Lists all daily csv.gz file keys for a given location and year."""
        prefix = f"records/csv.gz/locationid={location_id}/year={year}/"
        url = f"{S3_BASE_URL}/?prefix={prefix}&max-keys=1000"

        resp = self.session.get(url, timeout=20)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        keys = [c.find("s3:Key", S3_NS).text for c in root.findall("s3:Contents", S3_NS)]
        return sorted(keys)

    def _download_key(self, key: str) -> pd.DataFrame:
        """Downloads and decompresses a single daily csv.gz file."""
        file_url = f"{S3_BASE_URL}/{key}"
        for attempt in range(1, 4):
            try:
                resp = self.session.get(file_url, timeout=15)
                if resp.status_code == 200:
                    with gzip.open(io.BytesIO(resp.content), "rt", encoding="utf-8") as f:
                        return pd.read_csv(f)
            except Exception:
                time.sleep(0.5)
        return pd.DataFrame()

    def ingest_station(self, station_id: str, year: int = 2025) -> pd.DataFrame:
        """Downloads full year of physical sensor data for a station, aggregated to hourly."""
        meta = OPENAQ_STATIONS[station_id]
        loc_id = meta["location_id"]
        print(f"\n[CPCB Bulk] Querying S3 for {station_id} (ID: {loc_id}, Year: {year})...")

        keys = self._list_s3_keys(loc_id, year=year)
        print(f"[CPCB Bulk] Found {len(keys)} daily files.")
        if not keys:
            return pd.DataFrame()

        print(f"[CPCB Bulk] Downloading with {self.max_workers} threads...")
        dfs = []
        t0 = time.time()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._download_key, k): k for k in keys}
            for future in as_completed(futures):
                res = future.result()
                if not res.empty:
                    dfs.append(res)

        elapsed = time.time() - t0
        print(f"[CPCB Bulk] Downloaded {len(dfs)} files in {elapsed:.1f}s.")

        if not dfs:
            return pd.DataFrame()

        raw_df = pd.concat(dfs, ignore_index=True)

        # Filter to criteria pollutants
        raw_df["parameter"] = raw_df["parameter"].str.lower()
        raw_df = raw_df[raw_df["parameter"].isin(PARAM_MAP.keys())].copy()
        raw_df["param_std"] = raw_df["parameter"].map(PARAM_MAP)

        # Parse timestamps and clean values
        raw_df["datetime"] = pd.to_datetime(raw_df["datetime"], errors="coerce")
        raw_df = raw_df.dropna(subset=["datetime", "value"]).copy()
        raw_df["value"] = raw_df["value"].clip(lower=0.0)

        # Hourly aggregation (15-min readings → hourly mean)
        raw_df["timestamp"] = raw_df["datetime"].dt.floor("h")
        hourly_long = raw_df.groupby(["timestamp", "param_std"])["value"].mean().reset_index()

        # Pivot to wide format
        hourly_wide = hourly_long.pivot_table(
            index="timestamp", columns="param_std", values="value"
        ).reset_index()
        hourly_wide.columns.name = None

        # Attach metadata
        hourly_wide["station_id"] = station_id
        hourly_wide["station_name"] = meta["name"]
        hourly_wide["latitude"] = meta["latitude"]
        hourly_wide["longitude"] = meta["longitude"]

        # Compute official CPCB NAQI from physical measurements
        hourly_wide["cpcb_ground_naqi"] = compute_composite_naqi(hourly_wide)

        # Reorder columns
        cols = ["timestamp", "station_id", "station_name", "latitude", "longitude"]
        pollutant_cols = [c for c in ["pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide",
                                      "carbon_monoxide", "ozone"] if c in hourly_wide.columns]
        cols += pollutant_cols + ["cpcb_ground_naqi"]
        hourly_wide = hourly_wide[cols].sort_values("timestamp").reset_index(drop=True)

        return hourly_wide

    def run_all(self, year: int = 2025) -> pd.DataFrame:
        """Runs bulk ingestion for all Vidarbha CPCB stations."""
        print("=" * 80)
        print(f"STEP 01: BULK CPCB GROUND TRUTH INGESTION (YEAR: {year})")
        print("Source: OpenAQ Public S3 Archive")
        print("=" * 80)

        all_dfs = []
        for station_id in OPENAQ_STATIONS:
            df = self.ingest_station(station_id, year=year)
            if not df.empty:
                out_file = CPCB_RAW_DIR / f"cpcb_physical_{station_id.lower()}_{year}.csv"
                df.to_csv(out_file, index=False)
                print(f"[CPCB Bulk] [OK] {station_id}: {len(df):,} hourly records -> {out_file}")
                all_dfs.append(df)

        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            combined_file = CPCB_RAW_DIR / f"cpcb_physical_vidarbha_combined_{year}.csv"
            combined.to_csv(combined_file, index=False)
            print(f"\n[CPCB Bulk] [OK] Combined: {len(combined):,} rows -> {combined_file}")
            return combined
        return pd.DataFrame()


if __name__ == "__main__":
    CpcbBulkIngestion(max_workers=12).run_all(year=2025)
