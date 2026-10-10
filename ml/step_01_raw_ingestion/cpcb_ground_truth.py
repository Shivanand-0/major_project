"""
Authentic CPCB / MPCB Ground Truth Data Ingestion via WAQI API.
Uses the user's authentic token loaded from .env.
Fetches verified ground monitoring station readings (India NAQI & sub-pollutants).
"""

import os
import requests
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional

ENV_PATH = Path(r"d:\college_dev\.env")

# CPCB/MPCB Physical Station Mappings in Vidarbha
CPCB_STATION_UIDS = {
    "NAGPUR_CENTRAL": 12444,     # Opp GPO Civil Lines, Nagpur (MPCB)
    "CHANDRAPUR_MIDC": 9147,     # MIDC Khutala, Chandrapur (MPCB)
}

def load_waqi_token() -> str:
    """Loads WAQI token from .env or environment variable."""
    token = os.environ.get("WAQI_TOKEN")
    if not token and ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("WAQI_TOKEN") and "=" in line:
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not token:
        raise ValueError(
            "WAQI_TOKEN not found! Please ensure WAQI_TOKEN is set in d:\\college_dev\\.env or as an environment variable."
        )
    return token


class CPCBStationFeed:
    """Fetches authentic real-time ground truth CPCB readings."""

    BASE_URL = "https://api.waqi.info/feed"

    def __init__(self, token: Optional[str] = None):
        self.token = token or load_waqi_token()

    def get_station_reading(self, uid_or_keyword: Any) -> Dict[str, Any]:
        """Fetches latest station observation by UID or keyword."""
        if isinstance(uid_or_keyword, int):
            endpoint = f"{self.BASE_URL}/@{uid_or_keyword}/"
        else:
            endpoint = f"{self.BASE_URL}/{uid_or_keyword}/"
            
        params = {"token": self.token}
        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "ok":
            raise RuntimeError(f"WAQI API Error for {uid_or_keyword}: {data.get('data')}")
            
        return data["data"]

    def get_ground_truth_snapshot(self) -> pd.DataFrame:
        """Collects latest ground truth CPCB readings for available Vidarbha physical stations."""
        records = []
        for station_id, uid in CPCB_STATION_UIDS.items():
            try:
                d = self.get_station_reading(uid)
                iaqi = d.get("iaqi", {})
                records.append({
                    "station_id": station_id,
                    "cpcb_uid": uid,
                    "station_name": d.get("city", {}).get("name"),
                    "ground_cpcb_naqi": d.get("aqi"),
                    "observed_time": d.get("time", {}).get("s"),
                    "pm25": iaqi.get("pm25", {}).get("v"),
                    "pm10": iaqi.get("pm10", {}).get("v"),
                    "no2": iaqi.get("no2", {}).get("v"),
                    "so2": iaqi.get("so2", {}).get("v"),
                    "co": iaqi.get("co", {}).get("v"),
                    "o3": iaqi.get("o3", {}).get("v"),
                })
            except Exception as e:
                print(f"[CPCB Ground Truth] Could not fetch UID {uid} for {station_id}: {e}")
                
        return pd.DataFrame(records)


if __name__ == "__main__":
    client = CPCBStationFeed()
    df = client.get_ground_truth_snapshot()
    print("Latest CPCB Physical Ground Station Readings:")
    print(df.to_string())
