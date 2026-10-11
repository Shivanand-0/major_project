"""
LightGBM Training Engine for Step 05.
Fits a Gradient Boosted Decision Tree (GBDT) on authentic Vidarbha features.
Employs early stopping against the validation partition and evaluates on the winter holdout test set.
"""

import sys
import joblib
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple
from lightgbm import LGBMRegressor, early_stopping, log_evaluation
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Ensure ML root is in path for direct execution
_ML_ROOT = Path(__file__).resolve().parent.parent
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

try:
    from .config import (
        X_TRAIN_FILE, Y_TRAIN_FILE,
        X_VAL_FILE, Y_VAL_FILE,
        X_TEST_FILE, Y_TEST_FILE,
        MODELS_DIR,
        LGBM_PARAMS,
        EARLY_STOPPING_ROUNDS
    )
except (ImportError, ValueError):
    from step_05_batch_and_train.config import (
        X_TRAIN_FILE, Y_TRAIN_FILE,
        X_VAL_FILE, Y_VAL_FILE,
        X_TEST_FILE, Y_TEST_FILE,
        MODELS_DIR,
        LGBM_PARAMS,
        EARLY_STOPPING_ROUNDS
    )


class LightGBMTrainer:
    """Trains and benchmarks LightGBM regressor for India NAQI prediction."""

    def __init__(self, params: Dict[str, Any] = LGBM_PARAMS):
        self.params = params
        self.model = None

    def load_data(self) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """Loads train, validation, and test sets."""
        X_train = pd.read_csv(X_TRAIN_FILE)
        y_train = pd.read_csv(Y_TRAIN_FILE).squeeze("columns")

        X_val = pd.read_csv(X_VAL_FILE)
        y_val = pd.read_csv(Y_VAL_FILE).squeeze("columns")

        X_test = pd.read_csv(X_TEST_FILE)
        y_test = pd.read_csv(Y_TEST_FILE).squeeze("columns")

        return X_train, y_train, X_val, y_val, X_test, y_test

    def train(self) -> Dict[str, Any]:
        """Executes LightGBM model training with validation monitoring."""
        print("=" * 75)
        print("[TRAINING: LightGBM] Fitting Gradient Boosted Trees for India NAQI")
        print("=" * 75)

        X_train, y_train, X_val, y_val, X_test, y_test = self.load_data()
        feature_names = list(X_train.columns)
        print(f"[Data] Training Set  : {X_train.shape[0]:,} samples x {X_train.shape[1]} features")
        print(f"[Data] Validation Set: {X_val.shape[0]:,} samples")
        print(f"[Data] Out-of-Sample : {X_test.shape[0]:,} samples (Winter Inversion Test)")

        # Initialize regressor
        self.model = LGBMRegressor(**self.params)

        # Fit with early stopping
        callbacks = [
            early_stopping(stopping_rounds=EARLY_STOPPING_ROUNDS, verbose=False),
            log_evaluation(period=200)
        ]

        print("\n[Fitting] Training in progress...")
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            eval_names=["val"],
            callbacks=callbacks
        )

        best_iteration = self.model.best_iteration_
        print(f"[Optimal Trees] Best iteration reached at tree: {best_iteration}")

        # Predictions
        y_train_pred = self.model.predict(X_train)
        y_val_pred   = self.model.predict(X_val)
        y_test_pred  = self.model.predict(X_test)

        # Metric Calculations
        metrics = {
            "model_name": "LightGBM",
            "best_iteration": int(best_iteration),
            "train": {
                "rmse": round(float(np.sqrt(mean_squared_error(y_train, y_train_pred))), 3),
                "mae":  round(float(mean_absolute_error(y_train, y_train_pred)), 3),
                "r2":   round(float(r2_score(y_train, y_train_pred)), 4)
            },
            "val": {
                "rmse": round(float(np.sqrt(mean_squared_error(y_val, y_val_pred))), 3),
                "mae":  round(float(mean_absolute_error(y_val, y_val_pred)), 3),
                "r2":   round(float(r2_score(y_val, y_val_pred)), 4)
            },
            "test": {
                "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_test_pred))), 3),
                "mae":  round(float(mean_absolute_error(y_test, y_test_pred)), 3),
                "r2":   round(float(r2_score(y_test, y_test_pred)), 4)
            }
        }

        print("\n" + "-" * 50)
        print("LightGBM Performance Summary:")
        print(f"  * Train Set      -> R2: {metrics['train']['r2']:.4f} | MAE: {metrics['train']['mae']:.2f} | RMSE: {metrics['train']['rmse']:.2f}")
        print(f"  * Validation Set -> R2: {metrics['val']['r2']:.4f} | MAE: {metrics['val']['mae']:.2f} | RMSE: {metrics['val']['rmse']:.2f}")
        print(f"  * Test Set (Out) -> R2: {metrics['test']['r2']:.4f} | MAE: {metrics['test']['mae']:.2f} | RMSE: {metrics['test']['rmse']:.2f}")
        print("-" * 50)

        # Feature Importance
        importances = pd.DataFrame({
            "feature": feature_names,
            "importance_split": self.model.booster_.feature_importance(importance_type="split"),
            "importance_gain": self.model.booster_.feature_importance(importance_type="gain")
        }).sort_values(by="importance_gain", ascending=False).reset_index(drop=True)

        print("\nTop 7 Influential Modeling Features (by Information Gain):")
        for idx, row in importances.head(7).iterrows():
            print(f"  {idx+1}. {row['feature']:<30} (Gain: {row['importance_gain']:,.1f})")

        # Save Artifacts
        model_path = MODELS_DIR / "lgbm_model.joblib"
        importance_path = MODELS_DIR / "lgbm_feature_importance.csv"
        metrics_path = MODELS_DIR / "lgbm_metrics.json"

        joblib.dump(self.model, model_path)
        importances.to_csv(importance_path, index=False)
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)

        print(f"\n[Artifacts Saved]")
        print(f"  * Model       : {model_path}")
        print(f"  * Importances : {importance_path}")
        print(f"  * Metrics     : {metrics_path}")
        print("=" * 75)

        return metrics


if __name__ == "__main__":
    trainer = LightGBMTrainer()
    trainer.train()
