"""
Authentic Data Ingestion Orchestrator for Vidarbha Virtual Air Quality Grid.
Ingests ONLY 100% authentic measurements:
  - Historical Weather: ECMWF ERA5 Atmospheric Reanalysis
  - Historical Air Quality: Copernicus Atmosphere Monitoring Service (CAMS) Reanalysis
  - Live Realtime: Copernicus CAMS Operational Models + ECMWF Live Weather
  - Automatic computation of official CPCB India National AQI (NAQI)
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from step_01_raw_ingestion.config import (
    VIDARBHA_STATIONS,
    RAW_DATA_DIR,
    WEATHER_RAW_DIR,
    AQ_RAW_DIR,
    HISTORICAL_START_DATE,
    HISTORICAL_END_DATE
)
from step_01_raw_ingestion.weather_ingestion import AuthenticWeatherIngestion
from step_01_raw_ingestion.air_quality_ingestion import AuthenticAirQualityIngestion, get_naqi_category


class DataIngestionEngine:
    """
    Unified Data Ingestion Engine using 100% authentic meteorological and air quality sources.
    """

    def __init__(self):
        self.weather_client = AuthenticWeatherIngestion()
        self.aq_client = AuthenticAirQualityIngestion()

    def run_historical_ingestion(
        self,
        start_date: str = HISTORICAL_START_DATE,
        end_date: str = HISTORICAL_END_DATE
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Downloads authentic ERA5 meteorology and CAMS air quality datasets across Vidarbha nodes.
        """
        print("=" * 75)
        print(f"[STEP 01: AUTHENTIC INGESTION] Starting Download: {start_date} to {end_date}")
        print(f"[SOURCES] Weather: ECMWF ERA5 | AQ: Copernicus CAMS Reanalysis")
        print(f"[TARGETS] Stations: {list(VIDARBHA_STATIONS.keys())}")
        print("=" * 75)

        # 1. Weather Ingestion
        weather_df = self.weather_client.collect_all_historical_stations(output_dir=WEATHER_RAW_DIR)

        # 2. Air Quality Ingestion
        aq_df = self.aq_client.collect_all_historical_stations(output_dir=AQ_RAW_DIR)

        print("\n" + "=" * 75)
        print("[SUCCESS] Authentic Ingestion Completed Successfully!")
        print(f"[FILE] Weather: {WEATHER_RAW_DIR / 'weather_vidarbha_combined.csv'} ({len(weather_df):,} rows)")
        print(f"[FILE] Air Quality: {AQ_RAW_DIR / 'air_quality_vidarbha_combined.csv'} ({len(aq_df):,} rows)")
        print("=" * 75)

        return weather_df, aq_df

    def run_live_ingestion(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Fetches live real-time weather and authentic Copernicus CAMS air quality data for given coordinates.
        """
        print(f"[STEP 01: LIVE INGESTION] Ingesting Authentic Real-time Data for Coordinate ({lat:.4f}, {lon:.4f})...")
        live_weather = self.weather_client.fetch_live_weather(lat=lat, lon=lon)
        live_cams = self.aq_client.fetch_live_aq(lat=lat, lon=lon)

        return {
            "live_weather": live_weather,
            "live_aq": live_cams
        }


def main():
    parser = argparse.ArgumentParser(description="Step 01: Authentic Data Ingestion Engine")
    parser.add_argument("--mode", type=str, choices=["historical", "live"], default="historical",
                        help="Ingestion mode: 'historical' or 'live'")
    parser.add_argument("--start-date", type=str, default=HISTORICAL_START_DATE)
    parser.add_argument("--end-date", type=str, default=HISTORICAL_END_DATE)
    parser.add_argument("--lat", type=float, default=21.1458, help="Latitude (default: Nagpur Central)")
    parser.add_argument("--lon", type=float, default=79.0882, help="Longitude (default: Nagpur Central)")

    args = parser.parse_args()
    engine = DataIngestionEngine()

    if args.mode == "historical":
        engine.run_historical_ingestion(start_date=args.start_date, end_date=args.end_date)
    else:
        payload = engine.run_live_ingestion(lat=args.lat, lon=args.lon)
        latest_aq = payload["live_aq"].iloc[-1]
        latest_w = payload["live_weather"].iloc[-1]
        naqi_val = latest_aq.get("india_naqi", 0)
        category = get_naqi_category(naqi_val)

        print("\n" + "=" * 70)
        print(f"[LIVE SNAPSHOT] Coordinate ({args.lat}, {args.lon}) at {latest_aq['timestamp']}:")
        print("=" * 70)
        print(f"  * PM2.5 Physical Concentration : {latest_aq['pm2_5']} ug/m3")
        print(f"  * PM10 Physical Concentration  : {latest_aq['pm10']} ug/m3")
        print(f"  * Nitrogen Dioxide (NO2)       : {latest_aq['nitrogen_dioxide']} ug/m3")
        print(f"  * Sulphur Dioxide (SO2)        : {latest_aq['sulphur_dioxide']} ug/m3")
        print(f"  * Carbon Monoxide (CO)         : {latest_aq['carbon_monoxide']} ug/m3")
        print(f"  * Ozone (O3)                   : {latest_aq['ozone']} ug/m3")
        print(f"  * India National AQI (NAQI)    : {naqi_val} ({category})")
        if "us_aqi" in latest_aq:
            print(f"  * US EPA Standard AQI          : {latest_aq['us_aqi']}")
        print("-" * 70)
        print(f"  * Temperature (2m)             : {latest_w['temperature_2m']} C")
        print(f"  * Relative Humidity            : {latest_w['relative_humidity_2m']} %")
        print(f"  * Wind Speed                   : {latest_w['wind_speed_10m']} km/h")
        print(f"  * Wind Direction               : {latest_w['wind_direction_10m']} deg")
        print("=" * 70)


if __name__ == "__main__":
    main()
