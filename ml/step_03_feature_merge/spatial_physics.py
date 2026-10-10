"""
Spatial Transport Physics and Atmospheric Dispersion Vector Calculations.
Computes:
  1. Geodesic Haversine Distances to physical monitoring nodes.
  2. Compass Azimuth Bearings from station sources to target coordinates.
  3. Downwind Wind Dispersion Projections: W_downwind = Wind_Speed * cos(Wind_Dir - Bearing).
  4. Atmospheric transport & dilution indices.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Any

try:
    from step_01_raw_ingestion.config import VIDARBHA_STATIONS
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from step_01_raw_ingestion.config import VIDARBHA_STATIONS


class SpatialDispersionPhysics:
    """Computes spatial transport vectors and physical dispersion alignment."""

    EARTH_RADIUS_KM = 6371.0

    @classmethod
    def haversine_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Computes geodesic Haversine distance in kilometers between two coordinates."""
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)

        a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
        c = 2 * np.arcsin(np.clip(np.sqrt(a), 0, 1))
        return round(cls.EARTH_RADIUS_KM * c, 3)

    @classmethod
    def compute_bearing(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Computes forward compass azimuth bearing (0-360 degrees) from (lat1, lon1) to (lat2, lon2).
        """
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dlambda = np.radians(lon2 - lon1)

        x = np.sin(dlambda) * np.cos(phi2)
        y = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlambda)
        initial_bearing = np.degrees(np.arctan2(x, y))
        compass_bearing = (initial_bearing + 360) % 360
        return round(compass_bearing, 2)

    @classmethod
    def compute_downwind_transport(cls, wind_speed: float, wind_dir: float, source_lat: float, source_lon: float, target_lat: float, target_lon: float) -> Tuple[float, float]:
        """
        Computes downwind alignment and effective transport velocity.
        - alignment = cos(wind_dir - bearing) in [-1.0, 1.0]
        - transport_vector = wind_speed * alignment (positive means pollutant travels towards target)
        """
        bearing = cls.compute_bearing(source_lat, source_lon, target_lat, target_lon)
        angle_diff_rad = np.radians(wind_dir - bearing)
        alignment = float(np.cos(angle_diff_rad))
        transport_vector = float(wind_speed * alignment)
        return round(alignment, 3), round(transport_vector, 3)

    @classmethod
    def add_spatial_physics_features(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enriches the dataframe with distance and wind transport vectors relative to all Vidarbha physical stations.
        """
        df = df.copy()

        for st_name, meta in VIDARBHA_STATIONS.items():
            st_lat, st_lon = meta["latitude"], meta["longitude"]
            col_prefix = st_name.lower()

            # 1. Geodesic Distance
            dists = df.apply(lambda row: cls.haversine_distance(row["latitude"], row["longitude"], st_lat, st_lon), axis=1)
            df[f"dist_to_{col_prefix}_km"] = dists

            # 2. Inverse Distance Weight (IDW proxy)
            df[f"idw_weight_{col_prefix}"] = np.round(1.0 / (dists + 1.0) ** 2, 6)

            # 3. Downwind Transport Alignment
            if "wind_speed_10m" in df.columns and "wind_direction_10m" in df.columns:
                bearings = df.apply(lambda row: cls.compute_bearing(st_lat, st_lon, row["latitude"], row["longitude"]), axis=1)
                alignments = np.cos(np.radians(df["wind_direction_10m"] - bearings))
                df[f"wind_alignment_{col_prefix}"] = np.round(alignments, 3)
                df[f"downwind_dispersion_{col_prefix}"] = np.round(df["wind_speed_10m"] * alignments, 3)

        return df


if __name__ == "__main__":
    d = SpatialDispersionPhysics.haversine_distance(21.1458, 79.0882, 19.9615, 79.2961)
    b = SpatialDispersionPhysics.compute_bearing(21.1458, 79.0882, 19.9615, 79.2961)
    print(f"Nagpur to Chandrapur Distance: {d} km | Bearing: {b} deg")
