"""
Configuration for Step 03: Master Analytical Feature Merge.
Defines input cleaned data paths, real OpenStreetMap road infrastructure path,
and target master matrix outputs.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"

# Input files (Cleaned authentic datasets)
WEATHER_CLEAN_FILE = CLEAN_DIR / "weather_clean.csv"
AQ_CLEAN_FILE = CLEAN_DIR / "air_quality_clean.csv"
OSM_ROAD_FILE = RAW_DIR / "real_osm_road_network.json"

# Output Master Analytical Matrix
MASTER_MATRIX_FILE = CLEAN_DIR / "master_analytical_matrix.csv"
