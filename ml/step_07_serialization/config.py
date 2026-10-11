"""
Configuration for Step 07: Serialization.
Defines paths for model packaging, schema metadata, and production export artifacts.
"""

from pathlib import Path

# Base Paths (ml root)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = DATA_DIR / "models"
SPLIT_DIR = DATA_DIR / "split"
UNMONITORED_DIR = SPLIT_DIR / "unmonitored_deployment"
VALIDATION_DIR = DATA_DIR / "validation"
SERIALIZATION_DIR = BASE_DIR / "step_07_serialization"

# Input Models and Metadata
CHAMPION_MODEL_FILE = MODELS_DIR / "champion_model.joblib"
XGB_MODEL_FILE      = MODELS_DIR / "xgboost_model.joblib"
LGBM_MODEL_FILE     = MODELS_DIR / "lgbm_model.joblib"
SPLIT_METADATA_FILE = SPLIT_DIR / "split_metadata.json"
BENCHMARK_REPORT_FILE = MODELS_DIR / "training_benchmark_report.json"
VALIDATION_REPORT_FILE = VALIDATION_DIR / "validation_report.json"
X_TEST_FILE         = SPLIT_DIR / "X_test.csv"
Y_TEST_FILE         = SPLIT_DIR / "y_test.csv"
TEST_MATRIX_FILE    = SPLIT_DIR / "test_matrix.csv"

# Production Serialized Artifact
PIPELINE_MODEL_FILE = MODELS_DIR / "pipeline_model.joblib"
PIPELINE_METADATA_FILE = MODELS_DIR / "pipeline_metadata.json"

# Backend Direct Deployment Target Paths
BACKEND_DIR = BASE_DIR.parent / "backend"
BACKEND_MODELS_DIR = BACKEND_DIR / "models"
BACKEND_PIPELINE_MODEL_FILE = BACKEND_MODELS_DIR / "pipeline_model.joblib"
BACKEND_CHAMPION_MODEL_FILE = BACKEND_MODELS_DIR / "champion_model.joblib"
BACKEND_METADATA_FILE = BACKEND_MODELS_DIR / "pipeline_metadata.json"

# CPCB NAQI Categories & Color Mapping
CPCB_CATEGORIES = [
    {"min": 0,   "max": 50,  "category": "Good",         "color": "#00b050", "advisory": "Minimal impact on health."},
    {"min": 51,  "max": 100, "category": "Satisfactory", "color": "#92d050", "advisory": "Minor breathing discomfort to sensitive people."},
    {"min": 101, "max": 200, "category": "Moderate",     "color": "#ffff00", "advisory": "Breathing discomfort to people with lungs, asthma, and heart diseases."},
    {"min": 201, "max": 300, "category": "Poor",         "color": "#ff9900", "advisory": "Breathing discomfort to most people on prolonged exposure."},
    {"min": 301, "max": 400, "category": "Very Poor",    "color": "#ff0000", "advisory": "Respiratory illness on prolonged exposure."},
    {"min": 401, "max": 500, "category": "Severe",       "color": "#c00000", "advisory": "Affects healthy people and seriously impacts those with existing diseases."}
]
