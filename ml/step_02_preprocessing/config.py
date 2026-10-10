"""
Configuration for Step 02: Preprocessing.
Defines paths for authentic raw and clean datasets.
No hardcoded weights or synthetic profiles.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"

# Raw inputs (Fetched from ECMWF ERA5 & Copernicus CAMS APIs)
WEATHER_RAW_FILE = RAW_DIR / "weather" / "weather_vidarbha_combined.csv"
AQ_RAW_FILE = RAW_DIR / "air_quality" / "air_quality_vidarbha_combined.csv"

# Clean outputs
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
WEATHER_CLEAN_FILE = CLEAN_DIR / "weather_clean.csv"
AQ_CLEAN_FILE = CLEAN_DIR / "air_quality_clean.csv"
PREPROCESSED_MASTER_FILE = CLEAN_DIR / "preprocessed_features.csv"
