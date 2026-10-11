"""
Backend Configuration & Path Mappings.
Connects the backend FastAPI service to ML pipeline models and data registries.
"""

import sys
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
ML_DIR = PROJECT_ROOT / "ml"

# 1. Local Backend Models Directory (priority for Render / standalone cloud deployment)
BACKEND_MODELS_DIR = BACKEND_DIR / "models"
BACKEND_SERVICES_DIR = BACKEND_DIR / "services"

# 2. ML Pipeline Fallback Directory (for local development)
ML_MODELS_DIR = ML_DIR / "data" / "models"
ML_RAW_DIR = ML_DIR / "data" / "raw"
ML_VALIDATION_DIR = ML_DIR / "data" / "validation"

# Resolve Pipeline Model Path (prioritize backend/models)
if (BACKEND_MODELS_DIR / "pipeline_model.joblib").exists():
    PIPELINE_MODEL_PATH = BACKEND_MODELS_DIR / "pipeline_model.joblib"
elif (BACKEND_MODELS_DIR / "champion_model.joblib").exists():
    PIPELINE_MODEL_PATH = BACKEND_MODELS_DIR / "champion_model.joblib"
else:
    PIPELINE_MODEL_PATH = ML_MODELS_DIR / "pipeline_model.joblib"

# Resolve OSM Road Network Path (prioritize backend/models)
if (BACKEND_MODELS_DIR / "osm_road_network.json").exists():
    OSM_NETWORK_PATH = BACKEND_MODELS_DIR / "osm_road_network.json"
elif (BACKEND_MODELS_DIR / "real_osm_road_network.json").exists():
    OSM_NETWORK_PATH = BACKEND_MODELS_DIR / "real_osm_road_network.json"
elif (ML_RAW_DIR / "osm_roads" / "osm_road_network.json").exists():
    OSM_NETWORK_PATH = ML_RAW_DIR / "osm_roads" / "osm_road_network.json"
else:
    OSM_NETWORK_PATH = ML_RAW_DIR / "real_osm_road_network.json"

VALIDATION_REPORT_PATH = ML_VALIDATION_DIR / "realtime_validation_report.json"

# Ensure all relevant backend and ML paths are in sys.path so unpickling works
for p in [
    str(BACKEND_DIR),
    str(BACKEND_SERVICES_DIR),
    str(BACKEND_MODELS_DIR),
    str(ML_DIR),
    str(ML_DIR / "step_07_serialization"),
    str(ML_DIR / "step_01_raw_ingestion")
]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Pre-configured Vidarbha Grid Nodes
VIDARBHA_NODES = {
    "NAGPUR_CENTRAL": {
        "id": "NAGPUR_CENTRAL",
        "name": "Nagpur - Civil Lines / Central",
        "city": "Nagpur",
        "district": "Nagpur",
        "latitude": 21.1458,
        "longitude": 79.0882,
        "type": "physical",
        "station_name": "Civil Lines / Opp GPO (CPCB/MPCB)",
        "elevation_m": 310,
        "description": "Administrative center & commercial urban core with high traffic density."
    },
    "CHANDRAPUR_MIDC": {
        "id": "CHANDRAPUR_MIDC",
        "name": "Chandrapur - MIDC / Tadoba Corridor",
        "city": "Chandrapur",
        "district": "Chandrapur",
        "latitude": 19.9615,
        "longitude": 79.2961,
        "type": "physical",
        "station_name": "MIDC Khutala (CPCB/MPCB)",
        "elevation_m": 189,
        "description": "Industrial manufacturing belt with thermal power plants and coal mining emissions."
    },
    "AMRAVATI_CENTRAL": {
        "id": "AMRAVATI_CENTRAL",
        "name": "Amravati - Rajkamal Chowk / Camp",
        "city": "Amravati",
        "district": "Amravati",
        "latitude": 20.9374,
        "longitude": 77.7796,
        "type": "virtual",
        "station_name": "Virtual Sensor Node #1",
        "elevation_m": 343,
        "description": "Major educational hub & cotton market corridor; unmonitored by continuous physical CAAQMS."
    },
    "AKOLA_WEST": {
        "id": "AKOLA_WEST",
        "name": "Akola - Civil Lines / Industrial Area",
        "city": "Akola",
        "district": "Akola",
        "latitude": 20.7002,
        "longitude": 77.0082,
        "type": "virtual",
        "station_name": "Virtual Sensor Node #2",
        "elevation_m": 282,
        "description": "Agro-industrial center in western Vidarbha; unmonitored by continuous physical CAAQMS."
    }
}

# CPCB NAQI Categories & Color Mapping
CPCB_CATEGORIES = [
    {"min": 0,   "max": 50,  "category": "Good",         "color": "#00b050", "advisory": "Minimal impact on health."},
    {"min": 51,  "max": 100, "category": "Satisfactory", "color": "#92d050", "advisory": "Minor breathing discomfort to sensitive people."},
    {"min": 101, "max": 200, "category": "Moderate",     "color": "#ffff00", "advisory": "Breathing discomfort to people with lungs, asthma, and heart diseases."},
    {"min": 201, "max": 300, "category": "Poor",         "color": "#ff9900", "advisory": "Breathing discomfort to most people on prolonged exposure."},
    {"min": 301, "max": 400, "category": "Very Poor",    "color": "#ff0000", "advisory": "Respiratory illness on prolonged exposure."},
    {"min": 401, "max": 500, "category": "Severe",       "color": "#c00000", "advisory": "Affects healthy people and seriously impacts those with existing diseases."}
]

# Grid boundaries for Vidarbha spatial mapping
VIDARBHA_BOUNDS = {
    "min_lat": 19.5,
    "max_lat": 21.8,
    "min_lon": 76.5,
    "max_lon": 80.2
}
