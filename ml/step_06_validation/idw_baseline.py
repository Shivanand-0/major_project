"""
Inverse Distance Weighting (IDW) Spatial Baseline for Step 06: Validation.
Implements traditional non-machine-learning geospatial interpolation baseline.
Serves as the benchmark against which our Virtual Spatiotemporal ML model is evaluated.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates geodesic distance between two points in kilometers."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0)**2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return R * c


class IDWBaselineEvaluator:
    """
    Evaluates traditional Inverse Distance Weighting (IDW) spatial interpolation.
    Interpolates AQI based strictly on Euclidean/geodesic distance without considering
    wind direction, boundary layer inversion, or local traffic physics.
    """

    def __init__(self, power: float = 2.0):
        self.power = power

    def evaluate_cross_station(self, df_master: pd.DataFrame, station_a: str, station_b: str) -> Dict[str, Any]:
        """
        Evaluates IDW spatial transfer: Predicting station_b using station_a at identical timestamps.
        """
        sub_a = df_master[df_master["station_id"] == station_a].set_index("timestamp")["india_naqi"]
        sub_b = df_master[df_master["station_id"] == station_b].set_index("timestamp")["india_naqi"]

        common_idx = sub_a.index.intersection(sub_b.index)
        y_true = sub_b.loc[common_idx].values
        # In a 2-station setup, IDW interpolation simply maps station_a's value directly as the estimate for station_b
        y_pred = sub_a.loc[common_idx].values

        r2   = round(float(r2_score(y_true, y_pred)), 4)
        mae  = round(float(mean_absolute_error(y_true, y_pred)), 2)
        rmse = round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2)

        return {
            "source_station": station_a,
            "target_station": station_b,
            "sample_count": len(common_idx),
            "idw_r2": r2,
            "idw_mae": mae,
            "idw_rmse": rmse
        }
