"""
Configuration for Step 05: Batch & Train.
Defines paths, model hyperparameters, evaluation metrics, and artifact export locations.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SPLIT_DIR = DATA_DIR / "split"
LOSO_DIR = SPLIT_DIR / "loso_spatial_splits"
UNMONITORED_DIR = SPLIT_DIR / "unmonitored_deployment"
MODELS_DIR = DATA_DIR / "models"

# Ensure output model directory exists
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Training Input Files
X_TRAIN_FILE = SPLIT_DIR / "X_train.csv"
Y_TRAIN_FILE = SPLIT_DIR / "y_train.csv"
X_VAL_FILE   = SPLIT_DIR / "X_val.csv"
Y_VAL_FILE   = SPLIT_DIR / "y_val.csv"
X_TEST_FILE  = SPLIT_DIR / "X_test.csv"
Y_TEST_FILE  = SPLIT_DIR / "y_test.csv"

# Target Variable
TARGET_NAME = "india_naqi"

# LightGBM Regressor Hyperparameters
LGBM_PARAMS = {
    "objective": "regression",
    "metric": "rmse",
    "boosting_type": "gbdt",
    "learning_rate": 0.03,
    "n_estimators": 1200,
    "num_leaves": 31,
    "max_depth": 7,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "n_jobs": -1,
    "verbose": -1
}

# XGBoost Regressor Hyperparameters
XGB_PARAMS = {
    "objective": "reg:squarederror",
    "eval_metric": "rmse",
    "learning_rate": 0.03,
    "n_estimators": 1200,
    "max_depth": 6,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "n_jobs": -1
}

# Early Stopping Buffer
EARLY_STOPPING_ROUNDS = 50
