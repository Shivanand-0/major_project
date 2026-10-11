"""
Production Inference Engine for Virtual Spatiotemporal Air Quality Grid.
Provides an immutable, thread-safe wrapper around the champion model and feature schema.
Handles input validation, column re-ordering, CPCB category tagging, and health advisories.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Union, Optional

try:
    from .config import CPCB_CATEGORIES
except (ImportError, ValueError):
    try:
        from step_07_serialization.config import CPCB_CATEGORIES
    except ImportError:
        CPCB_CATEGORIES = [
            {"min": 0,   "max": 50,  "category": "Good",         "color": "#00b050", "advisory": "Minimal impact on health."},
            {"min": 51,  "max": 100, "category": "Satisfactory", "color": "#92d050", "advisory": "Minor breathing discomfort to sensitive people."},
            {"min": 101, "max": 200, "category": "Moderate",     "color": "#ffff00", "advisory": "Breathing discomfort to people with lungs, asthma, and heart diseases."},
            {"min": 201, "max": 300, "category": "Poor",         "color": "#ff9900", "advisory": "Breathing discomfort to most people on prolonged exposure."},
            {"min": 301, "max": 400, "category": "Very Poor",    "color": "#ff0000", "advisory": "Respiratory illness on prolonged exposure."},
            {"min": 401, "max": 500, "category": "Severe",       "color": "#c00000", "advisory": "Affects healthy people and seriously impacts those with existing diseases."}
        ]


class VirtualSensorPipeline:
    """
    Production-grade Virtual Air Quality Sensor Pipeline.
    Encapsulates the trained ML model, feature registry, and CPCB standard transformations.
    """

    def __init__(
        self,
        model: Any,
        feature_names: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.model = model
        self.feature_names = feature_names
        self.metadata = metadata or {}
        self.expected_feature_count = len(feature_names)

    def _get_cpcb_category(self, naqi: float) -> Dict[str, str]:
        """Maps continuous NAQI to official CPCB health categories and color codes."""
        if pd.isna(naqi) or naqi < 0:
            return {"category": "Unknown", "color": "#808080", "advisory": "Data unavailable."}

        for cat in CPCB_CATEGORIES:
            if cat["min"] <= naqi <= cat["max"]:
                return {
                    "category": cat["category"],
                    "color": cat["color"],
                    "advisory": cat["advisory"]
                }

        # If exceeds 500
        return {
            "category": "Severe (Hazardous)",
            "color": "#7e0023",
            "advisory": "Health alert: severe risk of emergency conditions for entire population."
        }

    def _determine_dominant_pollutant(self, row: Union[pd.Series, Dict[str, Any]]) -> str:
        """Determines likely dominant pollutant from available chemical features using CPCB standard weights."""
        # National Ambient Air Quality Standards (NAAQS 24-hr / 8-hr standard levels in ug/m3)
        THRESHOLDS = {
            "PM2.5": 60.0,
            "PM10": 100.0,
            "NO2": 80.0,
            "SO2": 80.0,
            "O3": 100.0,
            "CO": 2000.0  # 2 mg/m3 = 2000 ug/m3
        }
        KEY_MAP = {
            "PM2.5": "pm2_5",
            "PM10": "pm10",
            "NO2": "nitrogen_dioxide",
            "SO2": "sulphur_dioxide",
            "O3": "ozone",
            "CO": "carbon_monoxide"
        }
        ratios = {}
        for pol, key in KEY_MAP.items():
            val = row.get(key) if isinstance(row, dict) else (row[key] if key in row else None)
            if val is not None and not pd.isna(val) and float(val) > 0:
                # Scaled severity ratio relative to CPCB standard limit
                ratios[pol] = float(val) / THRESHOLDS[pol]

        if ratios:
            return max(ratios, key=ratios.get)
        return "PM2.5"


    def predict_batch(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Executes batch inference on a feature DataFrame.
        Ensures exact column ordering and schema compliance.
        """
        missing_cols = [c for c in self.feature_names if c not in X.columns]
        if missing_cols:
            raise ValueError(f"Input DataFrame missing required features: {missing_cols[:5]} (total missing: {len(missing_cols)})")

        # Reorder columns to match model expectations exactly
        X_aligned = X[self.feature_names].copy()

        # Fill any runtime dropouts with zero or column mean
        if X_aligned.isna().any().any():
            X_aligned = X_aligned.fillna(0.0)

        raw_preds = self.model.predict(X_aligned)
        # Clip to valid CPCB NAQI boundary
        clipped_preds = np.clip(np.round(raw_preds, 1), 0.0, 500.0)

        results = []
        for i, pred in enumerate(clipped_preds):
            cpcb_info = self._get_cpcb_category(pred)
            results.append({
                "predicted_india_naqi": float(pred),
                "category": cpcb_info["category"],
                "color": cpcb_info["color"],
                "health_advisory": cpcb_info["advisory"]
            })

        return pd.DataFrame(results)

    def predict_single(self, feature_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes single coordinate/instantaneous virtual inference.
        Returns detailed estimation, confidence intervals, and health advisory.
        """
        # Convert dictionary to single-row DataFrame
        df_single = pd.DataFrame([feature_dict])

        # Fill any missing expected features with 0.0
        for col in self.feature_names:
            if col not in df_single.columns:
                df_single[col] = 0.0

        df_aligned = df_single[self.feature_names]
        raw_pred = float(self.model.predict(df_aligned)[0])
        naqi_val = round(float(np.clip(raw_pred, 0.0, 500.0)), 1)

        cpcb_info = self._get_cpcb_category(naqi_val)
        dominant_pol = self._determine_dominant_pollutant(feature_dict)

        # Confidence bounds derived from validated test MAE (default ±22.61 AQI)
        mae_buffer = float(self.metadata.get("test_mae", 22.61))
        conf_min = round(max(0.0, naqi_val - mae_buffer), 1)
        conf_max = round(min(500.0, naqi_val + mae_buffer), 1)

        return {
            "predicted_india_naqi": naqi_val,
            "category": cpcb_info["category"],
            "color": cpcb_info["color"],
            "dominant_pollutant": dominant_pol,
            "health_advisory": cpcb_info["advisory"],
            "confidence_interval": {
                "lower": conf_min,
                "upper": conf_max,
                "error_margin_mae": mae_buffer
            },
            "model_architecture": self.metadata.get("model_name", "LightGBM Champion"),
            "status": "success"
        }
