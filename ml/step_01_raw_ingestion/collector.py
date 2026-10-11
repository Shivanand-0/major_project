"""
Data Ingestion Orchestrator for Step 01.
Coordinates all data source modules into a single entry point:
  1. WeatherIngestion       — ECMWF ERA5 & real-time Open-Meteo
  2. AirQualityIngestion    — Copernicus CAMS satellite atmospheric tracers
  3. CPCBStationFeed        — Official CPCB CCR Portal live observations
  4. CpcbBulkIngestion      — OpenAQ S3 historical CPCB physical data
  5. OpenStreetMapRoadIngestion — OSM Overpass road infrastructure
"""

import sys
import json
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple

# Ensure ML root is in path for direct execution
_ML_ROOT = Path(__file__).resolve().parent.parent
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

try:
    from .config import (
        VIDARBHA_STATIONS,
        RAW_DATA_DIR,
        WEATHER_RAW_DIR,
        AQ_RAW_DIR,
        CPCB_RAW_DIR,
        OSM_RAW_DIR,
        TRAINING_START_DATE,
        TRAINING_END_DATE,
        OSM_ROAD_FILE
    )
    from .weather_ingestion import WeatherIngestion
    from .air_quality_ingestion import AirQualityIngestion
    from .cpcb_ground_truth import CPCBStationFeed
    from .cpcb_bulk_ingestion import CpcbBulkIngestion
    from .osm_road_fetcher import OpenStreetMapRoadIngestion
    from .naqi import get_naqi_category
except (ImportError, ValueError):
    from step_01_raw_ingestion.config import (
        VIDARBHA_STATIONS,
        RAW_DATA_DIR,
        WEATHER_RAW_DIR,
        AQ_RAW_DIR,
        CPCB_RAW_DIR,
        OSM_RAW_DIR,
        TRAINING_START_DATE,
        TRAINING_END_DATE,
        OSM_ROAD_FILE
    )
    from step_01_raw_ingestion.weather_ingestion import WeatherIngestion
    from step_01_raw_ingestion.air_quality_ingestion import AirQualityIngestion
    from step_01_raw_ingestion.cpcb_ground_truth import CPCBStationFeed
    from step_01_raw_ingestion.cpcb_bulk_ingestion import CpcbBulkIngestion
    from step_01_raw_ingestion.osm_road_fetcher import OpenStreetMapRoadIngestion
    from step_01_raw_ingestion.naqi import get_naqi_category


class DataIngestionEngine:
    """
    Unified entry point for all raw data ingestion.
    Supports both historical (training data) and live (real-time prediction) modes.
    """

    def __init__(self):
        self.weather = WeatherIngestion()
        self.air_quality = AirQualityIngestion()
        self.cpcb_live = CPCBStationFeed()
        self.cpcb_bulk = CpcbBulkIngestion()
        self.osm = OpenStreetMapRoadIngestion()

    def run_historical_ingestion(
        self,
        start_date: str = TRAINING_START_DATE,
        end_date: str = TRAINING_END_DATE,
        year: int = 2025
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Downloads authentic raw datasets across all 4 Vidarbha stations:
          1. ECMWF ERA5 Weather
          2. Copernicus CAMS Air Quality
          3. OpenAQ Bulk CPCB Physical Ground Truth (Nagpur, Chandrapur, Amravati, Akola)
          4. OpenStreetMap Road Infrastructure
        """
        if start_date:
            try:
                year = int(start_date[:4])
            except ValueError:
                pass

        print("=" * 80)
        print(f"[STEP 01] HISTORICAL INGESTION (Period: {start_date} -> {end_date}, Year: {year})")
        print(f"[Stations] {list(VIDARBHA_STATIONS.keys())}")
        print("=" * 80)

        # 1. Weather
        print("\n>>> Phase 1/4: ECMWF ERA5 Atmospheric Reanalysis...")
        weather_df = self.weather.collect_all_stations(
            start_date=start_date, end_date=end_date
        )

        # 2. CAMS Air Quality
        print("\n>>> Phase 2/4: Copernicus CAMS Satellite Atmospheric Chemistry...")
        aq_df = self.air_quality.collect_all_stations(
            start_date=start_date, end_date=end_date
        )

        # 3. Bulk CPCB Physical Ground Truth
        print(f"\n>>> Phase 3/4: OpenAQ Bulk CPCB Ground Truth (Year: {year})...")
        cpcb_df = self.cpcb_bulk.run_all(year=year)

        # 4. OSM Roads
        print("\n>>> Phase 4/4: OpenStreetMap Infrastructure...")
        osm_dict = self.osm.fetch_all_stations()

        print("\n" + "=" * 80)
        print("[STEP 01] [OK] Historical ingestion complete across all 4 sources!")
        print(f"  Weather      : {len(weather_df):,} rows")
        print(f"  CAMS AQ      : {len(aq_df):,} rows")
        print(f"  CPCB Ground  : {len(cpcb_df):,} rows")
        print(f"  OSM Networks : {len(osm_dict)} stations")
        print("=" * 80)

        return weather_df, aq_df, cpcb_df, osm_dict

    def run_live_ingestion(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Fetches live real-time weather, CAMS air quality, CPCB ground truth,
        and OSM road context for a coordinate pair.
        """
        print("=" * 80)
        print(f"[STEP 01] Live Ingestion for ({lat:.4f}, {lon:.4f})")
        print("=" * 80)

        # 1. Live Weather
        print("[1/4] Fetching weather...")
        live_weather = self.weather.fetch_live(lat=lat, lon=lon)

        # 2. Live CAMS
        print("[2/4] Fetching CAMS air quality...")
        live_cams = self.air_quality.fetch_live(lat=lat, lon=lon)

        # 3. Live CPCB Ground Truth
        print("[3/4] Fetching CPCB ground truth...")
        cpcb_snap = self.cpcb_live.get_ground_truth_snapshot()
        cpcb_file = CPCB_RAW_DIR / "live_cpcb_snapshot.json"
        with open(cpcb_file, "w", encoding="utf-8") as f:
            json.dump(cpcb_snap.to_dict(orient="records"), f, indent=2)

        # 4. OSM Infrastructure
        print("[4/4] Fetching OSM road context...")
        osm_context = self.osm.fetch_road_infrastructure(lat=lat, lon=lon, radius_m=1200)

        payload = {
            "query_coordinates": {"lat": lat, "lon": lon},
            "timestamp_utc": pd.Timestamp.now("UTC").isoformat(),
            "live_weather": live_weather.to_dict(orient="records")[-1],
            "live_air_quality": live_cams.to_dict(orient="records")[-1],
            "osm_infrastructure": osm_context,
            "cpcb_ground_truth_snapshot": cpcb_snap.to_dict(orient="records")
        }

        snapshot_file = RAW_DATA_DIR / "live_telemetry_snapshot.json"
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        print(f"[STEP 01] [OK] Live snapshot saved -> {snapshot_file}")

        return payload


def main():
    parser = argparse.ArgumentParser(description="Step 01: Data Ingestion Engine")
    parser.add_argument("--mode", choices=["historical", "live"], default="live")
    parser.add_argument("--start-date", default=TRAINING_START_DATE)
    parser.add_argument("--end-date", default=TRAINING_END_DATE)
    parser.add_argument("--year", type=int, default=2025, help="Year for bulk CPCB ingestion")
    parser.add_argument("--lat", type=float, default=21.1458)
    parser.add_argument("--lon", type=float, default=79.0882)
    args = parser.parse_args()

    engine = DataIngestionEngine()

    if args.mode == "historical":
        engine.run_historical_ingestion(start_date=args.start_date, end_date=args.end_date, year=args.year)
    else:
        payload = engine.run_live_ingestion(lat=args.lat, lon=args.lon)
        aq = payload["live_air_quality"]
        w = payload["live_weather"]
        naqi_val = aq.get("india_naqi", 0)

        print(f"\n{'='*75}")
        print(f"[LIVE] ({args.lat}, {args.lon}) at {aq.get('timestamp')}:")
        print(f"  PM2.5={aq.get('pm2_5')} | PM10={aq.get('pm10')} | "
              f"NO2={aq.get('nitrogen_dioxide')} | SO2={aq.get('sulphur_dioxide')}")
        print(f"  CO={aq.get('carbon_monoxide')} | O3={aq.get('ozone')}")
        print(f"  India NAQI: {naqi_val} ({get_naqi_category(naqi_val)})")
        print(f"  Temp={w.get('temperature_2m')} C | RH={w.get('relative_humidity_2m')}% | "
              f"Wind={w.get('wind_speed_10m')}km/h @ {w.get('wind_direction_10m')} deg")
        print(f"{'='*75}")


if __name__ == "__main__":
    main()
