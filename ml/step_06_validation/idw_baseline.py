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

    STATION_COORDS = {
        "nagpur_central": (21.1458, 79.0882),
        "chandrapur_midc": (19.9615, 79.2961),
        "amravati_central": (20.9374, 77.7796),
        "akola_west": (20.7002, 77.0082),
        "NAGPUR_CENTRAL": (21.1458, 79.0882),
        "CHANDRAPUR_MIDC": (19.9615, 79.2961),
        "AMRAVATI_CENTRAL": (20.9374, 77.7796),
        "AKOLA_WEST": (20.7002, 77.0082)
    }

    def __init__(self, power: float = 2.0):
        self.power = power

    def evaluate_loso_idw(self, df_master: pd.DataFrame, target_station: str) -> Dict[str, Any]:
        """
        Evaluates leave-one-station-out IDW: Predicting target_station from all other stations.
        """
        norm_target = target_station.lower()
        pivot = df_master.pivot_table(index="timestamp", columns="station_id", values="india_naqi")
        # Normalize column names to lowercase
        pivot.columns = [str(c).lower() for c in pivot.columns]

        if norm_target not in pivot.columns:
            return {"error": f"Station {target_station} not found in matrix"}

        other_stations = [s for s in pivot.columns if s != norm_target and s in self.STATION_COORDS]
        target_lat, target_lon = self.STATION_COORDS[norm_target]

        distances = {}
        weights = {}
        for s in other_stations:
            s_lat, s_lon = self.STATION_COORDS[s]
            dist = max(haversine_distance_km(target_lat, target_lon, s_lat, s_lon), 1.0)
            distances[s] = dist
            weights[s] = 1.0 / (dist ** self.power)

        total_weight = sum(weights.values())
        norm_weights = {s: w / total_weight for s, w in weights.items()}

        sub = pivot[[norm_target] + other_stations].dropna()
        if len(sub) == 0:
            return {"error": "No overlapping timestamps"}

        y_true = sub[norm_target].values
        y_pred = np.zeros(len(sub))
        for s in other_stations:
            y_pred += sub[s].values * norm_weights[s]

        r2   = round(float(r2_score(y_true, y_pred)), 4)
        mae  = round(float(mean_absolute_error(y_true, y_pred)), 2)
        rmse = round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2)

        return {
            "target_station": norm_target,
            "sample_count": len(sub),
            "idw_r2": r2,
            "idw_mae": mae,
            "idw_rmse": rmse,
            "contributing_stations": other_stations
        }

