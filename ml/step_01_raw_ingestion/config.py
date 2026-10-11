"""
Centralized Configuration for the Vidarbha Air Quality ML Pipeline.
Single source of truth for all directory paths, station metadata,
API parameters, and ingestion date ranges across Steps 1–3.
"""

from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Directory Layout
# ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Raw data directories (written by Step 01)
RAW_DATA_DIR = DATA_DIR / "raw"
WEATHER_RAW_DIR = RAW_DATA_DIR / "weather"
AQ_RAW_DIR = RAW_DATA_DIR / "air_quality"
CPCB_RAW_DIR = RAW_DATA_DIR / "cpcb_ground_truth"
OSM_RAW_DIR = RAW_DATA_DIR / "osm_roads"

# Clean data directory (written by Step 02)
CLEAN_DIR = DATA_DIR / "clean"

# Ensure all directories exist on import
for _d in [WEATHER_RAW_DIR, AQ_RAW_DIR, CPCB_RAW_DIR, OSM_RAW_DIR, CLEAN_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# Raw file paths (Step 01 outputs)
# ─────────────────────────────────────────────────────────────
WEATHER_RAW_COMBINED = WEATHER_RAW_DIR / "weather_vidarbha_combined_2025.csv"
CAMS_RAW_COMBINED = AQ_RAW_DIR / "cams_vidarbha_combined_2025.csv"
CPCB_RAW_COMBINED = CPCB_RAW_DIR / "cpcb_physical_vidarbha_combined_2025.csv"
OSM_ROAD_FILE = OSM_RAW_DIR / "osm_road_network.json"

# ─────────────────────────────────────────────────────────────
# Clean file paths (Step 02 outputs → Step 03 inputs)
# ─────────────────────────────────────────────────────────────
WEATHER_CLEAN_FILE = CLEAN_DIR / "weather_clean_2025.csv"
CAMS_CLEAN_FILE = CLEAN_DIR / "cams_clean_2025.csv"
CPCB_CLEAN_FILE = CLEAN_DIR / "cpcb_physical_clean_2025.csv"

# ─────────────────────────────────────────────────────────────
# Master matrix (Step 03 output → Step 04 input)
# ─────────────────────────────────────────────────────────────
MASTER_MATRIX_FILE = CLEAN_DIR / "master_analytical_matrix_cpcb_2025.csv"

# ─────────────────────────────────────────────────────────────
# Vidarbha Physical Monitoring Stations
# ─────────────────────────────────────────────────────────────
VIDARBHA_STATIONS = {
    "NAGPUR_CENTRAL": {
        "name": "Nagpur - Civil Lines / Central",
        "district": "Nagpur",
        "latitude": 21.1458,
        "longitude": 79.0882,
        "station_type": "Urban / Commercial & Heavy Traffic",
    },
    "CHANDRAPUR_MIDC": {
        "name": "Chandrapur - MIDC / Tadoba Corridor",
        "district": "Chandrapur",
        "latitude": 19.9615,
        "longitude": 79.2961,
        "station_type": "Heavy Industrial / Thermal Power & Mining",
    },
    "AMRAVATI_CENTRAL": {
        "name": "Amravati - Rajkamal Chowk / Camp",
        "district": "Amravati",
        "latitude": 20.9374,
        "longitude": 77.7796,
        "station_type": "Mixed Urban / Commercial",
    },
    "AKOLA_WEST": {
        "name": "Akola - Civil Lines / Industrial Area",
        "district": "Akola",
        "latitude": 20.7002,
        "longitude": 77.0082,
        "station_type": "Semi-Urban / Agro-Industrial Corridor",
    }
}

# ─────────────────────────────────────────────────────────────
# Ingestion Date Ranges
# ─────────────────────────────────────────────────────────────
# Training data period (aligned with CPCB OpenAQ availability)
TRAINING_START_DATE = "2025-02-19"
TRAINING_END_DATE = "2025-12-31"

# ─────────────────────────────────────────────────────────────
# API Variable Lists
# ─────────────────────────────────────────────────────────────
# Open-Meteo ERA5 Weather variables
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

# Open-Meteo CAMS Air Quality variables
AQ_HOURLY_VARS = [
    "pm2_5",
    "pm10",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "carbon_monoxide"
]
