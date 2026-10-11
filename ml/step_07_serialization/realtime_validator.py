"""
Step 07.2: Real-Time Live Validation Engine.
Executes an end-to-end live test by:
  1. Fetching authentic live weather (ECMWF/Open-Meteo) and atmospheric chemistry (Copernicus CAMS) right now.
  2. Engineering live features (temporal harmonics, wind vectors, OSM roads, spatial downwind physics).
  3. Running live inference through the serialized 'pipeline_model.joblib'.
  4. Querying authentic live ground truth from physical CPCB stations (WAQI API).
  5. Generating a side-by-side Live Validation Report comparing Physical vs. Virtual Sensor AQI.
"""

import sys
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

IST = timezone(timedelta(hours=5, minutes=30))
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from step_01_raw_ingestion.config import VIDARBHA_STATIONS
from step_01_raw_ingestion.weather_ingestion import WeatherIngestion
from step_01_raw_ingestion.air_quality_ingestion import AirQualityIngestion
from step_01_raw_ingestion.cpcb_ground_truth import CPCBStationFeed
from step_01_raw_ingestion.naqi import compute_composite_naqi
from step_07_serialization.inference_engine import VirtualSensorPipeline

MODELS_DIR = BASE_DIR / "data" / "models"
VALIDATION_DIR = BASE_DIR / "data" / "validation"
PIPELINE_MODEL_FILE = MODELS_DIR / "pipeline_model.joblib"
OSM_FILE = BASE_DIR / "data" / "raw" / "osm_roads" / "osm_road_network.json"


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0)**2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return float(R * c)


def calculate_azimuth(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlambda = np.radians(lon2 - lon1)
    y = np.sin(dlambda) * np.cos(phi2)
    x = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlambda)
    bearing = np.degrees(np.arctan2(y, x))
    return float((bearing + 360.0) % 360.0)


class RealTimeValidator:
    """Orchestrates live real-time ingestion, virtual estimation, and CPCB ground validation."""

    def __init__(self):
        self.weather_client = WeatherIngestion()
        self.aq_client = AirQualityIngestion()
        self.cpcb_client = CPCBStationFeed()
        self.pipeline: VirtualSensorPipeline = joblib.load(PIPELINE_MODEL_FILE)

        # Load OSM cache
        with open(OSM_FILE, "r") as f:
            self.osm_data = json.load(f)

    def build_live_feature_vector(
        self,
        station_id: str,
        lat: float,
        lon: float,
        weather_row: pd.Series,
        aq_row: pd.Series
    ) -> Dict[str, Any]:
        """Constructs the exact 49-feature modeling vector from live readings."""
        now_ist = datetime.now(IST)
        hour = now_ist.hour
        dow = now_ist.weekday()
        month = now_ist.month

        # Weather vectors
        temp = float(weather_row.get("temperature_2m", 25.0))
        dew = float(weather_row.get("dew_point_2m", 15.0))
        spread = max(0.0, temp - dew)
        wind_speed = float(weather_row.get("wind_speed_10m", 5.0))
        wind_dir = float(weather_row.get("wind_direction_10m", 0.0))
        rad = np.radians(wind_dir)
        wind_u = round(-wind_speed * np.sin(rad), 3)
        wind_v = round(-wind_speed * np.cos(rad), 3)

        # Atmospheric chemical ratios
        no2 = float(aq_row.get("nitrogen_dioxide", 20.0))
        co = float(aq_row.get("carbon_monoxide", 300.0))
        combustion_ratio = round(no2 / (co + 1e-4), 5)

        # OSM Road features
        osm_entry = self.osm_data.get(station_id, {})
        osm_roads = osm_entry.get("roads", {})
        total_roads = osm_roads.get("total_roads", 500)
        major_highways = osm_roads.get("motorway", 0) + osm_roads.get("trunk", 0) + osm_roads.get("primary", 0)
        secondary_roads = osm_roads.get("secondary", 0) + osm_roads.get("tertiary", 0)
        road_density = round(total_roads / 78.54, 2)

        feat = {
            "temperature_2m": temp,
            "relative_humidity_2m": float(weather_row.get("relative_humidity_2m", 50.0)),
            "dew_point_2m": dew,
            "surface_pressure": float(weather_row.get("surface_pressure", 1010.0)),
            "wind_speed_10m": wind_speed,
            "wind_direction_10m": wind_dir,
            "wind_gusts_10m": float(weather_row.get("wind_gusts_10m", 10.0)),
            "precipitation": float(weather_row.get("precipitation", 0.0)),
            "cloud_cover": float(weather_row.get("cloud_cover", 20.0)),
            "direct_radiation": float(weather_row.get("direct_radiation", 0.0)),
            "latitude": lat,
            "longitude": lon,
            "dew_point_spread": spread,
            "wind_u": wind_u,
            "wind_v": wind_v,
            "sin_hour": round(float(np.sin(2 * np.pi * hour / 24.0)), 4),
            "cos_hour": round(float(np.cos(2 * np.pi * hour / 24.0)), 4),
            "sin_dayofweek": round(float(np.sin(2 * np.pi * dow / 7.0)), 4),
            "cos_dayofweek": round(float(np.cos(2 * np.pi * dow / 7.0)), 4),
            "sin_month": round(float(np.sin(2 * np.pi * month / 12.0)), 4),
            "cos_month": round(float(np.cos(2 * np.pi * month / 12.0)), 4),
            "is_weekend": int(dow >= 5),
            "pm2_5": float(aq_row.get("pm2_5", 35.0)),
            "pm10": float(aq_row.get("pm10", 60.0)),
            "nitrogen_dioxide": no2,
            "sulphur_dioxide": float(aq_row.get("sulphur_dioxide", 10.0)),
            "ozone": float(aq_row.get("ozone", 40.0)),
            "carbon_monoxide": co,
            "cams_satellite_naqi": float(compute_composite_naqi(pd.DataFrame([aq_row])).iloc[0]),
            "combustion_tracer_ratio": combustion_ratio,
            "osm_total_roads": total_roads,
            "osm_major_highways": major_highways,
            "osm_secondary_roads": secondary_roads,
            "osm_road_density_km2": road_density
        }

        # Spatial distances and downwind dispersion to all 4 network stations
        for target_id, target_meta in VIDARBHA_STATIONS.items():
            t_lat = target_meta["latitude"]
            t_lon = target_meta["longitude"]
            dist = haversine_distance(lat, lon, t_lat, t_lon)
            prefix = target_id.lower()

            feat[f"dist_to_{prefix}_km"] = round(dist, 2)
            idw_w = round(1.0 / (max(dist, 1.0)**2), 6)
            feat[f"idw_weight_{prefix}"] = idw_w

            if dist > 0.05:
                azimuth = calculate_azimuth(t_lat, t_lon, lat, lon)
                diff = np.radians(wind_dir - azimuth)
                alignment = round(float(np.cos(diff)), 3)
            else:
                alignment = 1.0

            feat[f"wind_alignment_{prefix}"] = alignment
            dispersion = round(float(wind_speed * alignment), 3)
            feat[f"downwind_dispersion_{prefix}"] = dispersion

        return feat

    def run_live_validation(self) -> Dict[str, Any]:
        print("=" * 85)
        print("STEP 07.2: REAL-TIME LIVE VALIDATION — VIRTUAL SENSOR vs. LIVE GROUND TRUTH")
        print(f"Timestamp (IST): {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 85)

        # 1. Fetch Live Physical Ground Truth from CPCB/MPCB
        print("\n[Ground Truth] Querying live CPCB physical stations (app.cpcbccr.com / official feeds)...")
        cpcb_snapshot = {}
        try:
            ground_df = self.cpcb_client.get_ground_truth_snapshot()
            for _, row in ground_df.iterrows():
                st_id = row["station_id"]
                cpcb_snapshot[st_id] = {
                    "station_name": row["station_name"],
                    "source": row.get("source", "CPCB Portal"),
                    "india_naqi": row.get("ground_india_naqi", row.get("ground_cpcb_naqi")),
                    "dominant_pollutant": row.get("dominant_pollutant"),
                    "sub_indices": row.get("sub_indices", {}),
                    "cpcb_pm25_subindex": row.get("cpcb_pm25_subindex"),
                    "observed_time": row["observed_time"],
                    "category": row.get("category", "N/A"),
                    "pm25": row.get("pm25"),
                    "pm10": row.get("pm10"),
                    "no2": row.get("no2"),
                    "so2": row.get("so2"),
                    "co": row.get("co"),
                    "o3": row.get("o3"),
                }
            print(f"[Ground Truth] Successfully retrieved {len(cpcb_snapshot)} active physical station feeds.")
        except Exception as e:
            print(f"[Ground Truth] Fetch note: {e}")

        # 2. Ingest Live Meteorology & Live CAMS Air Quality for All 4 Vidarbha Nodes
        print("\n[Live Ingestion] Fetching real-time ECMWF weather and Copernicus CAMS streams...")
        live_results = {}

        for station_id, meta in VIDARBHA_STATIONS.items():
            lat, lon = meta["latitude"], meta["longitude"]
            city_name = meta["name"]
            print(f"\nProcessing Node: {city_name} ({lat}, {lon})")

            # Fetch live streams
            w_df = self.weather_client.fetch_live_weather(lat, lon, station_id=station_id)
            aq_df = self.aq_client.fetch_live_aq(lat, lon, station_id=station_id)

            # Latest instantaneous observation
            latest_weather = w_df.iloc[-1]
            latest_aq = aq_df.iloc[-1]

            # Build feature vector
            feature_vector = self.build_live_feature_vector(
                station_id=station_id,
                lat=lat,
                lon=lon,
                weather_row=latest_weather,
                aq_row=latest_aq
            )

            # Predict via Virtual Sensor Pipeline
            prediction = self.pipeline.predict_single(feature_vector)
            pred_naqi = prediction["predicted_india_naqi"]
            pred_cat = prediction["category"]
            pred_color = prediction["color"]

            # Physical Ground Truth comparison if available
            ground_data = cpcb_snapshot.get(station_id, {})
            ground_naqi = ground_data.get("india_naqi")

            res_entry = {
                "station_id": station_id,
                "city_name": city_name,
                "coordinates": {"lat": lat, "lon": lon},
                "has_physical_station": station_id in cpcb_snapshot,
                "virtual_sensor_prediction": {
                    "predicted_india_naqi": pred_naqi,
                    "category": pred_cat,
                    "color": pred_color,
                    "confidence_interval": prediction["confidence_interval"],
                    "dominant_pollutant": prediction["dominant_pollutant"],
                    "health_advisory": prediction["health_advisory"]
                },
                "live_input_tracers": {
                    "cams_pm25": feature_vector["pm2_5"],
                    "cams_pm10": feature_vector["pm10"],
                    "cams_no2": feature_vector["nitrogen_dioxide"],
                    "temp_c": feature_vector["temperature_2m"],
                    "wind_speed_kmh": feature_vector["wind_speed_10m"],
                    "wind_dir_deg": feature_vector["wind_direction_10m"]
                }
            }

            if ground_naqi is not None:
                try:
                    g_val = float(ground_naqi)
                    diff = round(pred_naqi - g_val, 1)
                    abs_diff = round(abs(diff), 1)
                    
                    res_entry["cpcb_ground_truth"] = {
                        "observed_india_naqi": g_val,
                        "cpcb_category": ground_data.get("category"),
                        "dominant_pollutant": ground_data.get("dominant_pollutant"),
                        "sub_indices": ground_data.get("sub_indices"),
                        "observed_time": ground_data.get("observed_time"),
                        "station_name": ground_data.get("station_name"),
                        "source": ground_data.get("source"),
                        "ground_pollutants": {
                            "pm25": ground_data.get("pm25"),
                            "pm10": ground_data.get("pm10"),
                            "no2": ground_data.get("no2"),
                            "so2": ground_data.get("so2"),
                            "co": ground_data.get("co"),
                            "o3": ground_data.get("o3")
                        },
                        "residual_error": diff,
                        "absolute_error": abs_diff,
                        "within_model_mae_margin": abs_diff <= 15.0
                    }
                except (ValueError, TypeError):
                    pass

            live_results[station_id] = res_entry

        # 3. Print Side-by-Side Live Validation Summary Table
        print("\n" + "=" * 105)
        print("REAL-TIME LIVE VALIDATION REPORT: PHYSICAL CPCB GROUND TRUTH vs. VIRTUAL SENSOR")
        print("=" * 105)
        print(f"{'City / Node':<24} | {'CPCB India NAQI':<17} | {'Dominant':<10} | {'Virtual Predicted':<18} | {'Category':<14} | {'Live Residual':<12}")
        print("-" * 105)

        for st_id, data in live_results.items():
            name = data["city_name"]
            v_pred = f"{data['virtual_sensor_prediction']['predicted_india_naqi']:.1f}"
            cat = data["virtual_sensor_prediction"]["category"]

            if "cpcb_ground_truth" in data:
                g = data["cpcb_ground_truth"]
                g_obs = f"{g['observed_india_naqi']:.1f}"
                dom = str(g.get("dominant_pollutant", "PM2.5"))
                err = f"{g['residual_error']:+.1f} pts"
            else:
                g_obs = "[Unmonitored]"
                dom = "N/A"
                err = "N/A (Virtual)"

            print(f"{name:<24} | {g_obs:<17} | {dom:<10} | {v_pred:<18} | {cat:<14} | {err:<12}")

        print("=" * 105)

        # 4. Save Report to Disk
        report_file = VALIDATION_DIR / "realtime_validation_report.json"
        with open(report_file, "w") as f:
            json.dump({
                "timestamp_ist": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'),
                "pipeline_model": str(PIPELINE_MODEL_FILE),
                "nodes": live_results
            }, f, indent=2)

        print(f"\n[Artifact Saved] Live Validation Report: {report_file}")
        print("=" * 90)

        return live_results


if __name__ == "__main__":
    validator = RealTimeValidator()
    validator.run_live_validation()
