"""
Configuration for Step 06: Validation.
Defines paths, evaluation thresholds, baseline comparison parameters, and output directories.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SPLIT_DIR = DATA_DIR / "split"
LOSO_DIR = SPLIT_DIR / "loso_spatial_splits"
UNMONITORED_DIR = SPLIT_DIR / "unmonitored_deployment"
MODELS_DIR = DATA_DIR / "models"
VALIDATION_DIR = DATA_DIR / "validation"

# Ensure output validation directory exists
VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

# Model Artifacts
CHAMPION_MODEL_FILE = MODELS_DIR / "champion_model.joblib"
LGBM_MODEL_FILE = MODELS_DIR / "lgbm_model.joblib"
XGB_MODEL_FILE = MODELS_DIR / "xgboost_model.joblib"

# Evaluation Datasets
X_TEST_FILE = SPLIT_DIR / "X_test.csv"
Y_TEST_FILE = SPLIT_DIR / "y_test.csv"
TEST_MATRIX_FILE = SPLIT_DIR / "test_matrix.csv"

# Peak Winter Pollution Spike Thresholds (CPCB Categories)
MODERATE_THRESHOLD = 100.0   # NAQI > 100
POOR_THRESHOLD     = 200.0   # NAQI > 200
VERY_POOR_THRESHOLD= 300.0   # NAQI > 300
