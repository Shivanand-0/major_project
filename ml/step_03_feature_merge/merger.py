"""
Master Analytical Matrix Merger for Step 03.
Executes:
  1. Exact compound index join: [timestamp + station_id] on clean weather and air quality records.
  2. Integration of authentic OpenStreetMap physical road network infrastructure.
  3. Calculation of spatial proximity, Haversine distance matrix, and directional wind dispersion vectors.
  4. Generation of the immutable Master Analytical Matrix array for machine learning.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

try:
    from .config import (
        WEATHER_CLEAN_FILE,
        AQ_CLEAN_FILE,
        OSM_ROAD_FILE,
        MASTER_MATRIX_FILE
    )
    from .spatial_physics import SpatialDispersionPhysics
except ImportError:
    from config import (
        WEATHER_CLEAN_FILE,
        AQ_CLEAN_FILE,
        OSM_ROAD_FILE,
        MASTER_MATRIX_FILE
    )
    from spatial_physics import SpatialDispersionPhysics


class MasterMatrixMerger:
    """Merges authentic meteorological, air quality, OpenStreetMap roads, and spatial physics vectors."""

    def __init__(self):
        self.spatial_engine = SpatialDispersionPhysics()

    def merge_datasets(
        self,
        weather_path: Path = WEATHER_CLEAN_FILE,
        aq_path: Path = AQ_CLEAN_FILE,
        osm_path: Path = OSM_ROAD_FILE,
        output_path: Path = MASTER_MATRIX_FILE
    ) -> pd.DataFrame:
        """
        Merges weather, air quality, and spatial road matrices on [timestamp + station_id].
        """
        print("=" * 75)
        print("[STEP 03: FEATURE MERGE] Starting Master Analytical Matrix Construction")
        print("=" * 75)

        # 1. Load clean datasets
        print(f"[Loading] Clean Weather: {weather_path}")
        df_w = pd.read_csv(weather_path)
        print(f"[Loading] Clean Air Quality: {aq_path}")
        df_aq = pd.read_csv(aq_path)

        # Ensure datetime format
        df_w["timestamp"] = pd.to_datetime(df_w["timestamp"])
        df_aq["timestamp"] = pd.to_datetime(df_aq["timestamp"])

        # 2. Compound Index Join on [timestamp, station_id]
        print("[Join] Executing compound primary key join on [timestamp + station_id]...")
        # Avoid duplicate coordinate / source columns during merge
        aq_cols_to_use = [col for col in df_aq.columns if col not in ["latitude", "longitude", "data_source"]]
        df_merged = pd.merge(
            df_w,
            df_aq[aq_cols_to_use],
            on=["timestamp", "station_id"],
            how="inner"
        )
        print(f"[Join] Merged shape: {df_merged.shape[0]:,} rows x {df_merged.shape[1]} columns")

        # 3. Attach Real OpenStreetMap Road Infrastructure
        if osm_path.exists():
            print(f"[Enrichment] Attaching real OpenStreetMap road infrastructure from {osm_path}...")
            with open(osm_path, "r") as f:
                osm_data = json.load(f)

            df_merged["osm_total_roads"] = df_merged["station_id"].map(lambda sid: osm_data.get(sid, {}).get("total_road_segments", 0))
            df_merged["osm_major_highways"] = df_merged["station_id"].map(lambda sid: osm_data.get(sid, {}).get("major_highways_count", 0))
            df_merged["osm_secondary_roads"] = df_merged["station_id"].map(lambda sid: osm_data.get(sid, {}).get("secondary_roads_count", 0))
            df_merged["osm_road_density_km2"] = df_merged["station_id"].map(lambda sid: osm_data.get(sid, {}).get("road_density_per_sqkm", 0.0))
        else:
            print("[Warning] OSM road network file not found. Setting defaults.")
            df_merged["osm_road_density_km2"] = 100.0

        # 4. Attach Spatial Proximity & Downwind Dispersion Physics
        print("[Physics] Computing Haversine distances, azimuth bearings, and downwind transport vectors...")
        df_master = self.spatial_engine.add_spatial_physics_features(df_merged)

        # 5. Sort chronologically and by station
        df_master = df_master.sort_values(by=["timestamp", "station_id"]).reset_index(drop=True)

        # 6. Save Master Matrix
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_master.to_csv(output_path, index=False)

        print("\n" + "=" * 75)
        print("[SUCCESS] Master Analytical Matrix Created Successfully!")
        print(f"[FILE] Output File : {output_path}")
        print(f"[DIMS] Final Shape : {df_master.shape[0]:,} rows x {df_master.shape[1]} feature columns")
        print("=" * 75)

        return df_master


if __name__ == "__main__":
    merger = MasterMatrixMerger()
    master_df = merger.merge_datasets()
    print("Master Matrix Snapshot:")
    print(master_df[["timestamp", "station_id", "pm2_5", "temperature_2m", "wind_speed_10m", "osm_road_density_km2", "downwind_dispersion_nagpur_central"]].head(4))
