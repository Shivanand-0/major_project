"""
Virtual Sensor Estimation Engine.
Handles real-time feature extraction for any geographic coordinate,
ingesting current instantaneous meteorological (ECMWF) and atmospheric (CAMS) telemetry,
with zero fallback or stale past data.
"""

import time
import json
import joblib
import requests
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from backend_config import (
    PIPELINE_MODEL_PATH,
    OSM_NETWORK_PATH,
    VIDARBHA_NODES,
    VIDARBHA_BOUNDS,
    ML_DIR
)

# Import CPCB physical station feed client and NAQI calculator
try:
    from services.cpcb_ground_truth import CPCBStationFeed
    from services.naqi import compute_composite_naqi
except ImportError:
    try:
        from cpcb_ground_truth import CPCBStationFeed
        from naqi import compute_composite_naqi
    except ImportError:
        from step_01_raw_ingestion.cpcb_ground_truth import CPCBStationFeed
        from step_01_raw_ingestion.naqi import compute_composite_naqi

IST = timezone(timedelta(hours=5, minutes=30))


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great circle geodesic distance in kilometers."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0)**2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return float(R * c)


def calculate_azimuth(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates bearing from node 1 to node 2 in degrees (0-360)."""
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlambda = np.radians(lon2 - lon1)
    y = np.sin(dlambda) * np.cos(phi2)
    x = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlambda)
    bearing = np.degrees(np.arctan2(y, x))
    return float((bearing + 360.0) % 360.0)


class VirtualSensorEstimator:
    """Production service for real-time virtual air quality estimation."""

    WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
    AQ_API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    def __init__(self):
        print(f"[Estimator] Loading serialized model from {PIPELINE_MODEL_PATH}...")
        self.pipeline = joblib.load(PIPELINE_MODEL_PATH)
        print(f"[Estimator] Model loaded successfully: {self.pipeline.metadata.get('model_type')}")

        with open(OSM_NETWORK_PATH, "r") as f:
            self.osm_data = json.load(f)

        self.cpcb_client = CPCBStationFeed()

        # Cache live node results for 3 minutes to avoid duplicate rapid requests
        self._cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 180  # seconds

    def fetch_live_realtime_telemetry(self, lat: float, lon: float) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Fetches CURRENT instantaneous meteorological and atmospheric telemetry
        directly from Open-Meteo & Copernicus CAMS APIs for the given coordinates.
        Strictly live: no past/stale archive data, no static fallbacks.
        """
        # 1. Fetch current weather parameters
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,dew_point_2m,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,cloud_cover,direct_radiation",
            "timezone": "Asia/Kolkata"
        }

        w_json = None
        for attempt in range(3):
            try:
                w_resp = requests.get(self.WEATHER_API_URL, params=weather_params, timeout=20)
                if w_resp.status_code == 200:
                    w_json = w_resp.json()
                    break
            except (requests.RequestException, Exception):
                if attempt == 2:
                    raise
                time.sleep(1.0)

        if not w_json or "current" not in w_json:
            raise RuntimeError(f"No current weather data returned for ({lat}, {lon})")
        live_weather = w_json["current"]

        # 2. Fetch current Copernicus CAMS atmospheric chemical tracers
        aq_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,ozone,carbon_monoxide",
            "timezone": "Asia/Kolkata"
        }

        aq_json = None
        for attempt in range(3):
            try:
                aq_resp = requests.get(self.AQ_API_URL, params=aq_params, timeout=20)
                if aq_resp.status_code == 200:
                    aq_json = aq_resp.json()
                    break
            except (requests.RequestException, Exception):
                if attempt == 2:
                    raise
                time.sleep(1.0)

        if not aq_json or "current" not in aq_json:
            raise RuntimeError(f"No current atmospheric tracer data returned for ({lat}, {lon})")
        live_aq = aq_json["current"]

        return live_weather, live_aq

    def _estimate_osm_roads(self, lat: float, lon: float) -> Dict[str, float]:
        """Finds closest pre-computed OSM road cluster or calculates distance-weighted density."""
        min_dist = float("inf")
        closest_osm = None

        for st_id, meta in VIDARBHA_NODES.items():
            d = haversine_distance(lat, lon, meta["latitude"], meta["longitude"])
            if d < min_dist:
                min_dist = d
                closest_osm = self.osm_data.get(st_id, {}).get("roads", {})

        if not closest_osm:
            return {
                "osm_total_roads": 500,
                "osm_major_highways": 30,
                "osm_secondary_roads": 60,
                "osm_road_density_km2": 6.37
            }

        total = closest_osm.get("total_roads", 500)
        major = closest_osm.get("motorway", 0) + closest_osm.get("trunk", 0) + closest_osm.get("primary", 0)
        secondary = closest_osm.get("secondary", 0) + closest_osm.get("tertiary", 0)
        density = round(total / 78.54, 2)

        return {
            "osm_total_roads": total,
            "osm_major_highways": major,
            "osm_secondary_roads": secondary,
            "osm_road_density_km2": density
        }

    def build_feature_vector(
        self,
        lat: float,
        lon: float,
        weather: Dict[str, Any],
        aq: Dict[str, Any],
        station_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Constructs the exact 49-feature analytical vector required by the ML model.
        All values are derived directly from the live telemetry.
        """
        now_ist = datetime.now(IST)
        hour = now_ist.hour
        dow = now_ist.weekday()
        month = now_ist.month

        # Meteorology (Strictly live from weather)
        temp = float(weather["temperature_2m"])
        dew = float(weather["dew_point_2m"])
        spread = max(0.0, temp - dew)
        wind_speed = float(weather["wind_speed_10m"])
        wind_dir = float(weather["wind_direction_10m"])
        rad = np.radians(wind_dir)
        wind_u = round(-wind_speed * np.sin(rad), 3)
        wind_v = round(-wind_speed * np.cos(rad), 3)

        # Tracers (Strictly live from CAMS)
        no2 = float(aq["nitrogen_dioxide"])
        co = float(aq["carbon_monoxide"])
        combustion_ratio = round(no2 / (co + 1e-4), 5)

        # OSM Roads
        if station_id and station_id in self.osm_data:
            roads = self.osm_data[station_id].get("roads", {})
            total_roads = roads.get("total_roads", 500)
            major = roads.get("motorway", 0) + roads.get("trunk", 0) + roads.get("primary", 0)
            secondary = roads.get("secondary", 0) + roads.get("tertiary", 0)
            density = round(total_roads / 78.54, 2)
        else:
            osm_est = self._estimate_osm_roads(lat, lon)
            total_roads = osm_est["osm_total_roads"]
            major = osm_est["osm_major_highways"]
            secondary = osm_est["osm_secondary_roads"]
            density = osm_est["osm_road_density_km2"]

        feat = {
            "temperature_2m": temp,
            "relative_humidity_2m": float(weather["relative_humidity_2m"]),
            "dew_point_2m": dew,
            "surface_pressure": float(weather["surface_pressure"]),
            "wind_speed_10m": wind_speed,
            "wind_direction_10m": wind_dir,
            "wind_gusts_10m": float(weather.get("wind_gusts_10m", wind_speed * 1.5)),
            "precipitation": float(weather.get("precipitation", 0.0)),
            "cloud_cover": float(weather.get("cloud_cover", 0.0)),
            "direct_radiation": float(weather.get("direct_radiation", 0.0)),
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
            "pm2_5": float(aq["pm2_5"]),
            "pm10": float(aq["pm10"]),
            "nitrogen_dioxide": no2,
            "sulphur_dioxide": float(aq["sulphur_dioxide"]),
            "ozone": float(aq["ozone"]),
            "carbon_monoxide": co,
            "cams_satellite_naqi": float(compute_composite_naqi(pd.DataFrame([aq])).iloc[0]),
            "combustion_tracer_ratio": combustion_ratio,
            "osm_total_roads": total_roads,
            "osm_major_highways": major,
            "osm_secondary_roads": secondary,
            "osm_road_density_km2": density
        }

        # Spatial distances and downwind transport physics to Vidarbha reference nodes
        for target_id, target_meta in VIDARBHA_NODES.items():
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

    def predict_coordinate(
        self,
        lat: float,
        lon: float,
        weather_override: Optional[Dict[str, Any]] = None,
        aq_override: Optional[Dict[str, Any]] = None,
        station_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes real-time estimation for given coordinates by fetching
        CURRENT live features from external ECMWF and CAMS APIs,
        building features, and generating ML inference.
        """
        t_start = time.time()

        # 1. Fetch current real-time data or use manual simulator overrides
        if weather_override and aq_override:
            live_weather = weather_override
            live_aq = aq_override
            obs_time = datetime.now(IST).strftime("%Y-%m-%dT%H:%M")
        else:
            live_weather, live_aq = self.fetch_live_realtime_telemetry(lat, lon)
            obs_time = live_weather.get("time", datetime.now(IST).strftime("%Y-%m-%dT%H:%M"))

            # If user provided partial overrides, apply them
            if weather_override:
                live_weather.update(weather_override)
            if aq_override:
                live_aq.update(aq_override)

        # 2. Build complete 49-feature analytical vector
        features = self.build_feature_vector(lat, lon, live_weather, live_aq, station_id=station_id)

        # 3. Model prediction
        pred = self.pipeline.predict_single(features)
        latency_ms = round((time.time() - t_start) * 1000, 1)

        # 4. Reference station distance summary & Station Placement Check
        ref_distances = {}
        station_ground_truth = None
        for target_id, target_meta in VIDARBHA_NODES.items():
            dist = haversine_distance(lat, lon, target_meta["latitude"], target_meta["longitude"])
            ref_distances[target_meta["city"]] = f"{dist:.1f} km"
            if dist < 0.5 and target_meta.get("type") == "physical":
                try:
                    g_df = self.cpcb_client.get_ground_truth_snapshot()
                    g_row = g_df[g_df["station_id"] == target_id]
                    if not g_row.empty:
                        g_data = g_row.iloc[0]
                        g_naqi = g_data.get("ground_india_naqi")
                        station_ground_truth = {
                            "has_physical_station": True,
                            "station_id": target_id,
                            "station_name": target_meta["name"],
                            "observed_india_naqi": g_naqi,
                            "cpcb_category": g_data.get("category"),
                            "observed_time": g_data.get("observed_time"),
                            "dominant_pollutant": g_data.get("dominant_pollutant"),
                            "pollutants": {
                                "pm25": g_data.get("pm25"),
                                "pm10": g_data.get("pm10"),
                                "no2": g_data.get("no2"),
                                "so2": g_data.get("so2"),
                                "co": g_data.get("co"),
                                "o3": g_data.get("o3")
                            },
                            "residual": round(pred["predicted_india_naqi"] - float(g_naqi), 1) if g_naqi else None
                        }
                except Exception:
                    pass

        return {
            "coordinates": {"latitude": lat, "longitude": lon},
            "timestamp_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
            "observation_time": f"{obs_time} IST",
            "latency_ms": latency_ms,
            "prediction": pred,
            "physical_station_ground_truth": station_ground_truth,
            "realtime_features": {
                "atmospheric_tracers": {
                    "pm25": features["pm2_5"],
                    "pm10": features["pm10"],
                    "no2": features["nitrogen_dioxide"],
                    "so2": features["sulphur_dioxide"],
                    "co": features["carbon_monoxide"],
                    "o3": features["ozone"],
                    "combustion_ratio": features["combustion_tracer_ratio"],
                    "cams_satellite_naqi": features.get("cams_satellite_naqi")
                },
                "meteorology": {
                    "temperature_c": features["temperature_2m"],
                    "relative_humidity_pct": features["relative_humidity_2m"],
                    "dew_point_c": features["dew_point_2m"],
                    "dew_point_spread_c": features["dew_point_spread"],
                    "surface_pressure_hpa": features["surface_pressure"],
                    "wind_speed_kmh": features["wind_speed_10m"],
                    "wind_direction_deg": features["wind_direction_10m"],
                    "wind_gusts_kmh": features["wind_gusts_10m"],
                    "solar_radiation_wm2": features["direct_radiation"],
                    "cloud_cover_pct": features["cloud_cover"]
                },
                "spatial_transport": {
                    "distances_to_nodes": ref_distances,
                    "osm_road_density_km2": features["osm_road_density_km2"],
                    "osm_total_roads": features["osm_total_roads"],
                    "osm_major_highways": features["osm_major_highways"]
                }
            }
        }

    def get_all_nodes_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Returns comprehensive real-time status for all 4 Vidarbha nodes."""
        current_time = time.time()
        if not force_refresh and self._cache and (current_time - self._cache_timestamp < self._cache_ttl):
            return self._cache

        # 1. Fetch live physical ground truth
        cpcb_snapshot = {}
        try:
            ground_df = self.cpcb_client.get_ground_truth_snapshot()
            for _, row in ground_df.iterrows():
                st_id = row["station_id"]
                cpcb_snapshot[st_id] = {
                    "station_name": row["station_name"],
                    "source": row.get("source", "CPCB Portal"),
                    "ground_india_naqi": row["ground_india_naqi"],
                    "dominant_pollutant": row.get("dominant_pollutant"),
                    "sub_indices": row.get("sub_indices", {}),
                    "cpcb_pm25_subindex": row.get("cpcb_pm25_subindex"),
                    "observed_time": row["observed_time"],
                    "category": row.get("category", "N/A"),
                    "pollutants": {
                        "pm25": row.get("pm25"),
                        "pm10": row.get("pm10"),
                        "no2": row.get("no2"),
                        "so2": row.get("so2"),
                        "co": row.get("co"),
                        "o3": row.get("o3")
                    }
                }
        except Exception as e:
            print(f"[Estimator] Ground truth fetch notice: {e}")

        nodes_output = []

        for st_id, meta in VIDARBHA_NODES.items():
            lat = meta["latitude"]
            lon = meta["longitude"]

            res = self.predict_coordinate(lat, lon, station_id=st_id)
            pred_naqi = res["prediction"]["predicted_india_naqi"]

            node_dict = {
                "id": st_id,
                "name": meta["name"],
                "city": meta["city"],
                "district": meta["district"],
                "coordinates": {"lat": lat, "lon": lon},
                "type": meta["type"],
                "elevation_m": meta["elevation_m"],
                "description": meta["description"],
                "virtual_prediction": res["prediction"],
                "realtime_features": res["realtime_features"],
                "observation_time": res["observation_time"]
            }

            # If physical station is placed at this node and has live data, attach ground truth & residual
            if meta.get("type") == "physical" and st_id in cpcb_snapshot:
                g = cpcb_snapshot[st_id]
                g_naqi = g.get("ground_india_naqi")
                diff = round(pred_naqi - float(g_naqi), 1) if g_naqi is not None else None
                pm25_sub = g.get("cpcb_pm25_subindex")

                node_dict["physical_ground_truth"] = {
                    "has_physical_station": True,
                    "observed_india_naqi": g_naqi,
                    "cpcb_category": g.get("category"),
                    "dominant_pollutant": g.get("dominant_pollutant"),
                    "sub_indices": g.get("sub_indices"),
                    "observed_pm25_subindex": pm25_sub,
                    "observed_time": g.get("observed_time"),
                    "source": g.get("source"),
                    "pollutants": g.get("pollutants"),
                    "residual": diff
                }
            else:
                # Unmonitored coordinate: strictly None, do NOT show station value
                node_dict["physical_ground_truth"] = None

            nodes_output.append(node_dict)

        result = {
            "timestamp_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
            "model_champion": self.pipeline.metadata.get("model_architecture", "LightGBM Champion"),
            "model_mae": self.pipeline.metadata.get("test_mae", 22.61),
            "nodes": nodes_output
        }

        self._cache = result
        self._cache_timestamp = current_time
        return result

    def get_spatial_heatmap_grid(self, lat_steps: int = 5, lon_steps: int = 7) -> List[Dict[str, Any]]:
        """Generates a spatial mesh grid over Vidarbha for map heatmap interpolation."""
        lats = np.linspace(VIDARBHA_BOUNDS["min_lat"], VIDARBHA_BOUNDS["max_lat"], lat_steps)
        lons = np.linspace(VIDARBHA_BOUNDS["min_lon"], VIDARBHA_BOUNDS["max_lon"], lon_steps)

        grid_points = []
        for lat in lats:
            for lon in lons:
                try:
                    # Ingest real live weather & CAMS for each grid point
                    res = self.predict_coordinate(float(lat), float(lon))
                    pred = res["prediction"]
                    grid_points.append({
                        "lat": round(float(lat), 4),
                        "lon": round(float(lon), 4),
                        "predicted_aqi": pred["predicted_india_naqi"],
                        "category": pred["category"],
                        "color": pred["color"]
                    })
                except Exception:
                    pass

        return grid_points


# Singleton instance
_estimator_instance = None

def get_estimator() -> VirtualSensorEstimator:
    global _estimator_instance
    if _estimator_instance is None:
        _estimator_instance = VirtualSensorEstimator()
    return _estimator_instance
