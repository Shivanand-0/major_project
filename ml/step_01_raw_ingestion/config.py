"""
Configuration file for Vidarbha Air Quality Monitoring Network.
Defines coordinates, metadata, API endpoints, and ingestion parameters.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
WEATHER_RAW_DIR = RAW_DATA_DIR / "weather"
AQ_RAW_DIR = RAW_DATA_DIR / "air_quality"

# Ensure directories exist
WEATHER_RAW_DIR.mkdir(parents=True, exist_ok=True)
AQ_RAW_DIR.mkdir(parents=True, exist_ok=True)

# Vidarbha Physical Monitoring Stations Dictionary
VIDARBHA_STATIONS = {
    "NAGPUR_CENTRAL": {
        "name": "Nagpur - Civil Lines / Central",
        "district": "Nagpur",
        "latitude": 21.1458,
        "longitude": 79.0882,
        "station_type": "Urban / Commercial & Heavy Traffic",
        "baseline_pm25_mean": 68.5,
        "traffic_weight": 0.90,
        "industrial_weight": 0.40,
    },
    "CHANDRAPUR_MIDC": {
        "name": "Chandrapur - MIDC / Tadoba Corridor",
        "district": "Chandrapur",
        "latitude": 19.9615,
        "longitude": 79.2961,
        "station_type": "Heavy Industrial / Thermal Power & Mining",
        "baseline_pm25_mean": 94.2,
        "traffic_weight": 0.65,
        "industrial_weight": 0.95,
    },
    "AMRAVATI_CENTRAL": {
        "name": "Amravati - Rajkamal Chowk / Camp",
        "district": "Amravati",
        "latitude": 20.9374,
        "longitude": 77.7796,
        "station_type": "Mixed Urban / Commercial",
        "baseline_pm25_mean": 52.0,
        "traffic_weight": 0.70,
        "industrial_weight": 0.30,
    },
    "AKOLA_WEST": {
        "name": "Akola - Civil Lines / Industrial Area",
        "district": "Akola",
        "latitude": 20.7002,
        "longitude": 77.0082,
        "station_type": "Semi-Urban / Agro-Industrial Corridor",
        "baseline_pm25_mean": 48.5,
        "traffic_weight": 0.55,
        "industrial_weight": 0.35,
    }
}

# Ingestion Date Parameters for Historical Training (1 full annual cycle + seasonal coverage)
HISTORICAL_START_DATE = "2023-01-01"
HISTORICAL_END_DATE = "2023-12-31"

# Weather API Variables (Open-Meteo)
WEATHER_HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "precipitation",
    "cloud_cover",
    "direct_radiation"
]

# Air Quality API Variables (Open-Meteo / CAMS / OpenAQ)
AQ_HOURLY_VARS = [
    "pm2_5",
    "pm10",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "carbon_monoxide"
]
