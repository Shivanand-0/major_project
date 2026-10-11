"""
CPCB Live Ground Truth Ingestion Module.
Fetches real-time hourly observations from physical CPCB / MPCB CAAQMS stations.

Primary Source: Official CPCB CCR Portal (app.cpcbccr.com) — live HTML scraping.
Fallback Source: WAQI API (if WAQI_TOKEN is set in environment or .env).

This module handles LIVE / REAL-TIME readings only.
For bulk historical CPCB data, use cpcb_bulk_ingestion.py (OpenAQ S3 archive).
"""

import os
import re
import requests
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# Ensure ML root is in path for direct execution
_ML_ROOT = Path(__file__).resolve().parent.parent
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

try:
    from .naqi import compute_subindex, get_naqi_category
except (ImportError, ValueError):
    from step_01_raw_ingestion.naqi import compute_subindex, get_naqi_category

IST = timezone(timedelta(hours=5, minutes=30))
ENV_PATH = Path(r"d:\college_dev\.env")

# CPCB / MPCB Physical Station URL Mappings for Vidarbha
CPCB_PORTAL_CITIES = {
    "NAGPUR_CENTRAL": {
        "url": "https://app.cpcbccr.com/in/maharashtra/nagpur-aqi",
        "station_name": "Nagpur Central / Civil Lines (CPCB/MPCB)",
        "city": "Nagpur",
        "waqi_uid": 12444
    },
    "CHANDRAPUR_MIDC": {
        "url": "https://app.cpcbccr.com/in/maharashtra/chandrapur-aqi",
        "station_name": "MIDC Khutala, Chandrapur (CPCB/MPCB)",
        "city": "Chandrapur",
        "waqi_uid": 9147
    }
}


def _load_env_var(key_name: str) -> Optional[str]:
    """Loads environment variable from system or .env file."""
    val = os.environ.get(key_name)
    if not val and ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key_name) and "=" in line:
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    return val


class CPCBStationFeed:
    """Fetches real-time ground truth CPCB readings from official portals."""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        self.waqi_token = _load_env_var("WAQI_TOKEN")

    def fetch_from_cpcb_portal(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Scrapes live hourly observations directly from official CPCB CCR portal."""
        meta = CPCB_PORTAL_CITIES.get(station_id)
        if not meta:
            return None

        try:
            resp = requests.get(meta["url"], headers=self.headers, timeout=12)
            if resp.status_code != 200:
                return None

            html = resp.text

            # Extract AQI number
            aqi_match = re.search(r'(\d+)\s*</span>\s*<span[^>]*>\s*US AQI', html)
            aqi_val = float(aqi_match.group(1)) if aqi_match else None

            # Extract update time
            update_match = re.search(r'Updated <!-- -->(\d+:\d+)<!-- --> local time', html)
            obs_time = update_match.group(1) if update_match else datetime.now(IST).strftime("%H:%M")

            # Extract category
            cat_match = re.search(r'rounded-full"[^>]*></span>([^<]+)</p>', html)
            category = cat_match.group(1).strip() if cat_match else "Moderate"

            # Extract pollutants
            pollutants = {}
            for p, std_key in [("PM2.5", "pm25"), ("PM10", "pm10"), ("NO₂", "no2"),
                               ("SO₂", "so2"), ("CO", "co"), ("O₃", "o3")]:
                p_esc = re.escape(p)
                p_match = re.search(rf'{p_esc}</p>.*?tabular-nums[^>]*>(\d+)<span', html, re.DOTALL)
                if p_match:
                    pollutants[std_key] = float(p_match.group(1))

            # Calculate authentic CPCB India NAQI from physical criteria pollutants
            sub_indices = {}
            for p_code, p_key in [("pm2_5", "pm25"), ("pm10", "pm10"), ("nitrogen_dioxide", "no2"),
                                  ("sulphur_dioxide", "so2"), ("carbon_monoxide", "co"), ("ozone", "o3")]:
                val = pollutants.get(p_key)
                if val is not None and not pd.isna(val):
                    sub = compute_subindex(float(val), p_code)
                    if sub is not None and not pd.isna(sub):
                        sub_indices[p_key] = round(float(sub), 1)

            if sub_indices:
                india_naqi_val = max(sub_indices.values())
                dominant_pol = max(sub_indices, key=sub_indices.get)
                category = get_naqi_category(india_naqi_val)
            else:
                india_naqi_val = aqi_val
                dominant_pol = "PM2.5"

            pm25 = pollutants.get("pm25")
            cpcb_pm25_sub = sub_indices.get("pm25")

            return {
                "station_id": station_id,
                "station_name": meta["station_name"],
                "source": "CPCB Official CCR Portal (Live)",
                "ground_india_naqi": india_naqi_val,
                "ground_cpcb_naqi": india_naqi_val,
                "dominant_pollutant": dominant_pol,
                "sub_indices": sub_indices,
                "cpcb_pm25_subindex": cpcb_pm25_sub,
                "observed_time": f"Today {obs_time} IST",
                "category": category,
                "pm25": pm25,
                "pm10": pollutants.get("pm10"),
                "no2": pollutants.get("no2"),
                "so2": pollutants.get("so2"),
                "co": pollutants.get("co"),
                "o3": pollutants.get("o3")
            }
        except Exception as e:
            print(f"[CPCB Portal] Error scraping {station_id}: {e}")
            return None

    def fetch_from_waqi(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Fallback: fetches station observation via WAQI API."""
        if not self.waqi_token:
            return None

        meta = CPCB_PORTAL_CITIES.get(station_id)
        if not meta or "waqi_uid" not in meta:
            return None

        uid = meta["waqi_uid"]
        try:
            resp = requests.get(f"https://api.waqi.info/feed/@{uid}/",
                                params={"token": self.waqi_token}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    d = data["data"]
                    iaqi = d.get("iaqi", {})
                    pollutants = {
                        "pm25": iaqi.get("pm25", {}).get("v"),
                        "pm10": iaqi.get("pm10", {}).get("v"),
                        "no2": iaqi.get("no2", {}).get("v"),
                        "so2": iaqi.get("so2", {}).get("v"),
                        "co": iaqi.get("co", {}).get("v"),
                        "o3": iaqi.get("o3", {}).get("v")
                    }

                    # Compute official CPCB India NAQI from physical pollutants
                    sub_indices = {}
                    for p_code, p_key in [("pm2_5", "pm25"), ("pm10", "pm10"), ("nitrogen_dioxide", "no2"),
                                          ("sulphur_dioxide", "so2"), ("carbon_monoxide", "co"), ("ozone", "o3")]:
                        val = pollutants.get(p_key)
                        if val is not None and not pd.isna(val):
                            sub = compute_subindex(float(val), p_code)
                            if sub is not None and not pd.isna(sub):
                                sub_indices[p_key] = round(float(sub), 1)

                    if sub_indices:
                        india_naqi_val = max(sub_indices.values())
                        dominant_pol = max(sub_indices, key=sub_indices.get)
                        category = get_naqi_category(india_naqi_val)
                    else:
                        india_naqi_val = d.get("aqi")
                        dominant_pol = "PM2.5"
                        category = "Moderate"

                    pm25 = pollutants.get("pm25")
                    return {
                        "station_id": station_id,
                        "station_name": d.get("city", {}).get("name", meta["station_name"]),
                        "source": "CPCB Physical Feed (WAQI)",
                        "ground_india_naqi": india_naqi_val,
                        "ground_cpcb_naqi": india_naqi_val,
                        "dominant_pollutant": dominant_pol,
                        "sub_indices": sub_indices,
                        "cpcb_pm25_subindex": sub_indices.get("pm25"),
                        "observed_time": d.get("time", {}).get("s"),
                        "category": category,
                        "pm25": pm25,
                        "pm10": pollutants.get("pm10"),
                        "no2": pollutants.get("no2"),
                        "so2": pollutants.get("so2"),
                        "co": pollutants.get("co"),
                        "o3": pollutants.get("o3")
                    }
        except Exception as e:
            print(f"[WAQI Fallback] Error fetching {uid}: {e}")
            return None

    def get_ground_truth_snapshot(self) -> pd.DataFrame:
        """Collects verified live ground truth readings for Vidarbha physical stations."""
        records = []
        for station_id in CPCB_PORTAL_CITIES.keys():
            reading = self.fetch_from_cpcb_portal(station_id)
            if not reading or reading.get("ground_india_naqi") is None:
                reading = self.fetch_from_waqi(station_id)
            if reading:
                records.append(reading)
        return pd.DataFrame(records)


if __name__ == "__main__":
    client = CPCBStationFeed()
    df = client.get_ground_truth_snapshot()
    print("=" * 80)
    print("LIVE CPCB GROUND TRUTH SNAPSHOT (INDIA NAQI):")
    print("=" * 80)
    for _, row in df.iterrows():
        print(f"\n{row['station_name']} ({row['station_id']})")
        print(f"  Source: {row['source']} | Time: {row['observed_time']}")
        print(f"  India NAQI: {row['ground_india_naqi']} ({row.get('category', 'N/A')}) | Dominant: {row.get('dominant_pollutant')}")
        print(f"  Sub-indices: {row.get('sub_indices')}")
        print(f"  Raw Concentrations: PM2.5={row['pm25']}, PM10={row['pm10']}, NO2={row['no2']}, "
              f"SO2={row['so2']}, CO={row['co']}, O3={row['o3']}")
