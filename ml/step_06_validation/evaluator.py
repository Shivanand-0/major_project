"""
Comprehensive Validation & Diagnostic Evaluation Engine for Step 06.
Evaluates:
  1. Full Statistical Performance on Out-of-Sample Winter Holdout (Nov-Dec 2023).
  2. Peak Winter Pollution Spike Analysis (NAQI > 100, NAQI > 150, NAQI > 200).
  3. Residual Distribution & Error Quartiles (Percentage within ±5 and ±10 AQI points).
  4. Benchmark comparison against traditional Inverse Distance Weighting (IDW) baseline.
  5. Artifact export: validation_report.json and predictions_vs_actual.csv.
"""

import joblib
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    median_absolute_error,
    r2_score
)

try:
    from .config import (
        BASE_DIR,
        CHAMPION_MODEL_FILE,
        X_TEST_FILE,
        Y_TEST_FILE,
        TEST_MATRIX_FILE,
        VALIDATION_DIR,
        MODELS_DIR,
        SPLIT_DIR,
        MODERATE_THRESHOLD,
        POOR_THRESHOLD
    )
    from .idw_baseline import IDWBaselineEvaluator
except ImportError:
    from config import (
        BASE_DIR,
        CHAMPION_MODEL_FILE,
        X_TEST_FILE,
        Y_TEST_FILE,
        TEST_MATRIX_FILE,
        VALIDATION_DIR,
        MODELS_DIR,
        SPLIT_DIR,
        MODERATE_THRESHOLD,
        POOR_THRESHOLD
    )
    from idw_baseline import IDWBaselineEvaluator


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Computes Mean Absolute Percentage Error (MAPE) avoiding division by zero."""
    mask = y_true > 1.0
    return round(float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0), 2)


class ModelValidationEngine:
    """Performs deep diagnostic validation and baseline benchmarking for the Virtual Sensor."""

    def __init__(self, model_path: Path = CHAMPION_MODEL_FILE):
        self.model_path = model_path
        self.idw_evaluator = IDWBaselineEvaluator()

    def run_validation(self) -> Dict[str, Any]:
        print("=" * 80)
        print("STEP 06: VALIDATION & DIAGNOSTIC BENCHMARKING")
        print("=" * 80)

        # 1. Load Model and Datasets
        print(f"[Loading] Champion Model: {self.model_path}")
        model = joblib.load(self.model_path)

        print(f"[Loading] Test Features: {X_TEST_FILE}")
        X_test = pd.read_csv(X_TEST_FILE)
        y_test = pd.read_csv(Y_TEST_FILE).squeeze("columns").values
        test_matrix = pd.read_csv(TEST_MATRIX_FILE)

        # 2. Generate Predictions
        y_pred = model.predict(X_test)
        residuals = y_test - y_pred
        abs_errors = np.abs(residuals)

        # 3. Overall Test Metrics
        r2   = round(float(r2_score(y_test, y_pred)), 4)
        rmse = round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 2)
        mae  = round(float(mean_absolute_error(y_test, y_pred)), 2)
        medae= round(float(median_absolute_error(y_test, y_pred)), 2)
        mape = calculate_mape(y_test, y_pred)
        corr = round(float(np.corrcoef(y_test, y_pred)[0, 1]), 4)

        print("\n" + "-" * 60)
        print("1. OVERALL OUT-OF-SAMPLE TEST PERFORMANCE (NOV-DEC 2023):")
        print("-" * 60)
        print(f"  • Sample Count           : {len(y_test):,} hourly records")
        print(f"  • Coefficient of Determ. : R² = {r2:.4f}")
        print(f"  • Pearson Correlation    : r  = {corr:.4f}")
        print(f"  • Mean Absolute Error    : MAE = {mae:.2f} AQI points")
        print(f"  • Root Mean Squared Error: RMSE = {rmse:.2f} AQI points")
        print(f"  • Median Absolute Error  : MedAE = {medae:.2f} AQI points")
        print(f"  • Mean Abs. Pct Error    : MAPE = {mape:.2f}%")

        # 4. Error Tolerance Distributions
        pct_within_5  = round(float((abs_errors <= 5.0).mean() * 100.0), 2)
        pct_within_10 = round(float((abs_errors <= 10.0).mean() * 100.0), 2)
        pct_within_15 = round(float((abs_errors <= 15.0).mean() * 100.0), 2)

        print("\n" + "-" * 60)
        print("2. ERROR TOLERANCE RESIDUAL SPREAD:")
        print("-" * 60)
        print(f"  • Predictions within ±5 AQI points  : {pct_within_5}%")
        print(f"  • Predictions within ±10 AQI points : {pct_within_10}%")
        print(f"  • Predictions within ±15 AQI points : {pct_within_15}%")
        print(f"  • Mean Bias Error (Signed)         : {float(residuals.mean()):.2f} AQI points")
        print(f"  • 95th Percentile Error            : {float(np.percentile(abs_errors, 95)):.2f} AQI points")

        # 5. Peak Winter Pollution Spike Analysis
        print("\n" + "-" * 60)
        print("3. PEAK WINTER POLLUTION SPIKE SUBSET ANALYSIS:")
        print("-" * 60)

        spike_tiers = {
            "Standard (NAQI <= 100)": y_test <= 100.0,
            "Moderate Inversion (100 < NAQI <= 150)": (y_test > 100.0) & (y_test <= 150.0),
            "Heavy Inversion Spikes (NAQI > 150)": y_test > 150.0,
            "Extreme Episode Spikes (NAQI > 200)": y_test > 200.0
        }

        tier_metrics = {}
        for tier_name, mask in spike_tiers.items():
            count = int(mask.sum())
            if count > 0:
                t_r2   = round(float(r2_score(y_test[mask], y_pred[mask])), 4)
                t_mae  = round(float(mean_absolute_error(y_test[mask], y_pred[mask])), 2)
                t_rmse = round(float(np.sqrt(mean_squared_error(y_test[mask], y_pred[mask]))), 2)
                tier_metrics[tier_name] = {
                    "sample_count": count,
                    "percentage_of_test": round(count / len(y_test) * 100.0, 1),
                    "r2": t_r2,
                    "mae": t_mae,
                    "rmse": t_rmse
                }
                print(f"  • {tier_name:<38}: n={count:>4} ({count/len(y_test)*100:>4.1f}%) | MAE={t_mae:>5.2f} | RMSE={t_rmse:>5.2f} | R²={t_r2:>6.4f}")

        # 6. IDW Spatial Baseline Comparison
        print("\n" + "-" * 60)
        print("4. BENCHMARK COMPARISON: VIRTUAL SENSOR vs. IDW BASELINE:")
        print("-" * 60)

        # Load master cleaned matrix for direct station-to-station IDW
        clean_master_file = BASE_DIR / "data" / "clean" / "master_analytical_matrix_cpcb_2025.csv"
        df_master = pd.read_csv(clean_master_file)

        # Load our ML Cross-Station Transfer results from Step 05 report
        bench_report_file = MODELS_DIR / "training_benchmark_report.json"
        with open(bench_report_file, "r") as f:
            bench_data = json.load(f)
        ml_transfer = bench_data.get("spatial_cross_station_transfer", {})

        stations = ["nagpur_central", "chandrapur_midc", "amravati_central", "akola_west"]
        idw_results = {}
        ml_holdout_results = {}
        idw_maes = []
        ml_maes = []

        for st in stations:
            idw_res = self.idw_evaluator.evaluate_loso_idw(df_master, st)
            idw_results[st] = idw_res
            if "idw_mae" in idw_res:
                idw_maes.append(idw_res["idw_mae"])

            ml_res = ml_transfer.get(f"holdout_{st}", {})
            ml_holdout_results[st] = ml_res
            if "mae" in ml_res:
                ml_maes.append(ml_res["mae"])

            print(f"  • Station {st:<18}: IDW MAE = {idw_res.get('idw_mae', 'N/A')} (R²={idw_res.get('idw_r2', 'N/A')}) | ML Holdout MAE = {ml_res.get('mae', 'N/A')} (R²={ml_res.get('r2', 'N/A')})")

        idw_mae_avg = round(float(np.mean(idw_maes)), 2) if idw_maes else 0.0
        ml_mae_avg  = round(float(np.mean(ml_maes)), 2) if ml_maes else 0.0
        error_reduction_pct = round(((idw_mae_avg - ml_mae_avg) / idw_mae_avg) * 100.0, 1) if idw_mae_avg > 0 else 0.0

        print(f"\n  • 4-Station Average IDW Spatial MAE : {idw_mae_avg:.2f} AQI points")
        print(f"  • 4-Station Average ML Spatial MAE  : {ml_mae_avg:.2f} AQI points")
        print(f"  • ERROR REDUCTION OVER TRADITIONAL IDW : {error_reduction_pct}% IMPROVEMENT!")

        # 7. Export Evaluation Artifacts
        df_eval = test_matrix[["timestamp", "station_id"]].copy()
        df_eval["actual_india_naqi"] = np.round(y_test, 1)
        df_eval["predicted_india_naqi"] = np.round(y_pred, 1)
        df_eval["residual_error"] = np.round(residuals, 2)
        df_eval["absolute_error"] = np.round(abs_errors, 2)

        pred_csv = VALIDATION_DIR / "predictions_vs_actual.csv"
        df_eval.to_csv(pred_csv, index=False)

        champ_name = bench_data.get("champion_model", "Champion")
        validation_summary = {
            "model_evaluated": f"{champ_name} Champion",
            "overall_test_metrics": {
                "sample_count": len(y_test),
                "r2": r2,
                "pearson_r": corr,
                "mae": mae,
                "rmse": rmse,
                "medae": medae,
                "mape": mape
            },
            "error_distribution": {
                "pct_within_5_pts": pct_within_5,
                "pct_within_10_pts": pct_within_10,
                "pct_within_15_pts": pct_within_15,
                "mean_bias_error": round(float(residuals.mean()), 3),
                "std_error": round(float(residuals.std()), 3),
                "p95_error": round(float(np.percentile(abs_errors, 95)), 2)
            },
            "winter_spike_tiers": tier_metrics,
            "idw_baseline_comparison": {
                "idw_average_mae": idw_mae_avg,
                "ml_average_mae": ml_mae_avg,
                "error_reduction_percentage": error_reduction_pct,
                "station_idw_results": idw_results,
                "station_ml_results": ml_holdout_results
            }
        }

        report_json = VALIDATION_DIR / "validation_report.json"
        with open(report_json, "w") as f:
            json.dump(validation_summary, f, indent=2)

        print("\n" + "=" * 80)
        print("[SUCCESS] Step 06 Validation Completed Successfully!")
        print(f"  • Predictions CSV : {pred_csv}")
        print(f"  • Report JSON     : {report_json}")
        print("=" * 80)

        return validation_summary


if __name__ == "__main__":
    validator = ModelValidationEngine()
    validator.run_validation()
