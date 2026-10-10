"""
Master Training Orchestrator for Step 05: Batch & Train.
Orchestrates:
  1. LightGBM & XGBoost chronological window training.
  2. Side-by-side model benchmarking (RMSE, MAE, R²).
  3. Spatial Cross-Station Transfer (LOSO) evaluation (Nagpur <-> Chandrapur).
  4. Champion model selection and deployment packaging.
"""

import joblib
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any

try:
    from .config import (
        MODELS_DIR,
        SPLIT_DIR,
        LOSO_DIR
    )
    from .train_lgbm import LightGBMTrainer
    from .train_xgboost import XGBoostTrainer
except ImportError:
    from config import (
        MODELS_DIR,
        SPLIT_DIR,
        LOSO_DIR
    )
    from train_lgbm import LightGBMTrainer
    from train_xgboost import XGBoostTrainer

from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from lightgbm import LGBMRegressor


class TrainingPipelineOrchestrator:
    """Orchestrates comprehensive multi-model training and spatial generalization testing."""

    def __init__(self):
        self.lgbm_trainer = LightGBMTrainer()
        self.xgb_trainer = XGBoostTrainer()

    def run_spatial_transfer_benchmark(self, model_class=LGBMRegressor) -> Dict[str, Any]:
        """
        Tests Cross-Station Spatial Transfer (Nagpur <-> Chandrapur).
        Proves how accurately the model infers AQI for a city not seen during training.
        """
        print("\n" + "=" * 75)
        print("[SPATIAL EVALUATION] Benchmarking Cross-Station Transfer Generalization")
        print("=" * 75)

        holdouts = [
            ("nagpur_central", "chandrapur_midc"),
            ("chandrapur_midc", "nagpur_central")
        ]

        loso_results = {}
        for test_st, train_st in holdouts:
            x_train_file = LOSO_DIR / f"X_train_holdout_{test_st}.csv"
            y_train_file = LOSO_DIR / f"y_train_holdout_{test_st}.csv"
            x_test_file  = LOSO_DIR / f"X_test_holdout_{test_st}.csv"
            y_test_file  = LOSO_DIR / f"y_test_holdout_{test_st}.csv"

            if not (x_train_file.exists() and x_test_file.exists()):
                continue

            X_tr = pd.read_csv(x_train_file)
            y_tr = pd.read_csv(y_train_file).squeeze("columns")
            X_te = pd.read_csv(x_test_file)
            y_te = pd.read_csv(y_test_file).squeeze("columns")

            # Fit model on training city only
            m = model_class(n_estimators=600, learning_rate=0.03, max_depth=7, num_leaves=31, random_state=42, verbose=-1)
            m.fit(X_tr, y_tr)
            y_pred = m.predict(X_te)

            r2   = round(float(r2_score(y_te, y_pred)), 4)
            mae  = round(float(mean_absolute_error(y_te, y_pred)), 2)
            rmse = round(float(np.sqrt(mean_squared_error(y_te, y_pred))), 2)

            loso_results[f"train_{train_st}_test_{test_st}"] = {
                "train_station": train_st,
                "test_station": test_st,
                "test_rows": len(y_te),
                "r2": r2,
                "mae": mae,
                "rmse": rmse
            }
            print(f"  • Trained exclusively on {train_st.upper()} -> Inferred {test_st.upper()} : R² = {r2:.4f} | MAE = {mae:.2f} | RMSE = {rmse:.2f}")

        return loso_results

    def run_full_training_pipeline(self) -> Dict[str, Any]:
        """Runs complete Step 05 training pipeline."""
        print("*" * 80)
        print("STEP 05: BATCH & TRAIN — MACHINE LEARNING ESTIMATION PIPELINE")
        print("*" * 80)

        # 1. Train LightGBM
        lgbm_metrics = self.lgbm_trainer.train()

        # 2. Train XGBoost
        xgb_metrics = self.xgb_trainer.train()

        # 3. Spatial Cross-Station Transfer Benchmark
        spatial_metrics = self.run_spatial_transfer_benchmark()

        # 4. Compare Models
        print("\n" + "=" * 80)
        print("MODEL COMPARISON (CHRONOLOGICAL OUT-OF-SAMPLE WINTER TEST SET)")
        print("=" * 80)
        print(f"{'Model':<15} | {'Test R²':<10} | {'Test MAE':<10} | {'Test RMSE':<10} | {'Val R²':<10}")
        print("-" * 80)
        print(f"{'LightGBM':<15} | {lgbm_metrics['test']['r2']:<10.4f} | {lgbm_metrics['test']['mae']:<10.2f} | {lgbm_metrics['test']['rmse']:<10.2f} | {lgbm_metrics['val']['r2']:<10.4f}")
        print(f"{'XGBoost':<15} | {xgb_metrics['test']['r2']:<10.4f} | {xgb_metrics['test']['mae']:<10.2f} | {xgb_metrics['test']['rmse']:<10.2f} | {xgb_metrics['val']['r2']:<10.4f}")
        print("=" * 80)

        # 5. Select Champion Model
        if lgbm_metrics['test']['r2'] >= xgb_metrics['test']['r2']:
            champion_name = "LightGBM"
            champion_metrics = lgbm_metrics
            champion_model_file = MODELS_DIR / "lgbm_model.joblib"
        else:
            champion_name = "XGBoost"
            champion_metrics = xgb_metrics
            champion_model_file = MODELS_DIR / "xgboost_model.joblib"

        # Copy/Save champion model as champion_model.joblib
        champion_dest = MODELS_DIR / "champion_model.joblib"
        champion_obj = joblib.load(champion_model_file)
        joblib.dump(champion_obj, champion_dest)

        print(f"\n[Champion Selected]: {champion_name} (Highest Out-of-Sample R²: {champion_metrics['test']['r2']:.4f})")
        print(f"[Champion Artifact]: {champion_dest}")

        # Save Final Benchmark Report
        benchmark_report = {
            "champion_model": champion_name,
            "lightgbm": lgbm_metrics,
            "xgboost": xgb_metrics,
            "spatial_cross_station_transfer": spatial_metrics
        }

        report_file = MODELS_DIR / "training_benchmark_report.json"
        with open(report_file, "w") as f:
            json.dump(benchmark_report, f, indent=2)

        print(f"[Benchmark Report]: {report_file}")
        print("*" * 80)

        return benchmark_report


if __name__ == "__main__":
    orchestrator = TrainingPipelineOrchestrator()
    orchestrator.run_full_training_pipeline()
