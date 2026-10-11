"""
Master Analytical Matrix Merger for Step 03.
Joins clean datasets from Step 02 into a single training-ready matrix:
  1. Weather + CAMS satellite features (inner join on timestamp + station_id)
  2. Physical CPCB ground truth labels (spatiotemporal match)
  3. OSM road infrastructure metrics
  4. Spatial dispersion physics (Haversine, IDW, wind transport vectors)
"""

import sys
import json
import pandas as pd
from pathlib import Path

# Ensure ML root is on path for direct script execution
_ML_ROOT = Path(__file__).resolve().parent.parent
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

from step_01_raw_ingestion.config import (
    WEATHER_CLEAN_FILE,
    CAMS_CLEAN_FILE,
    CPCB_CLEAN_FILE,
    OSM_ROAD_FILE,
    MASTER_MATRIX_FILE,
)
try:
    from .spatial_physics import SpatialDispersionPhysics
except ImportError:
    from spatial_physics import SpatialDispersionPhysics


class MasterMatrixMerger:
    """Merges weather, CAMS, CPCB ground truth, OSM roads, and spatial physics into one matrix."""

    def merge(
        self,
        weather_path: Path = WEATHER_CLEAN_FILE,
        cams_path: Path = CAMS_CLEAN_FILE,
        cpcb_path: Path = CPCB_CLEAN_FILE,
        osm_path: Path = OSM_ROAD_FILE,
        output_path: Path = MASTER_MATRIX_FILE,
    ) -> pd.DataFrame:
        """
        Executes the full spatiotemporal merge pipeline.

        Steps:
            1. Merge Weather + CAMS on [timestamp, station_id]
            2. Join with CPCB ground truth labels on [timestamp, station_id]
            3. Attach OSM road infrastructure per station
            4. Compute spatial physics features
            5. Export master analytical matrix
        """
        print("=" * 80)
        print("STEP 03: MASTER ANALYTICAL MATRIX CONSTRUCTION")
        print("=" * 80)

        # 1. Load clean datasets
        print(f"[Load] Weather: {weather_path}")
        df_w = pd.read_csv(weather_path)
        df_w["timestamp"] = pd.to_datetime(df_w["timestamp"])

        print(f"[Load] CAMS: {cams_path}")
        df_cams = pd.read_csv(cams_path)
        df_cams["timestamp"] = pd.to_datetime(df_cams["timestamp"])

        print(f"[Load] CPCB Ground Truth: {cpcb_path}")
        df_cpcb = pd.read_csv(cpcb_path)
        df_cpcb["timestamp"] = pd.to_datetime(df_cpcb["timestamp"])

        # 2. Merge Weather + CAMS (avoid duplicate coordinate columns)
        cams_cols = [c for c in df_cams.columns if c not in ["latitude", "longitude"]]
        df_cams_clean = df_cams[cams_cols].copy()
        if "india_naqi" in df_cams_clean.columns:
            df_cams_clean.rename(columns={"india_naqi": "cams_satellite_naqi"}, inplace=True)

        df_predictors = pd.merge(df_w, df_cams_clean, on=["timestamp", "station_id"], how="inner")
        print(f"[Merge] Weather + CAMS: {df_predictors.shape[0]:,} rows x {df_predictors.shape[1]} cols")

        # 3. Join with CPCB ground truth (physical analyzer target)
        cpcb_sub = df_cpcb[["timestamp", "station_id", "cpcb_ground_naqi"]].copy()
        cpcb_sub.rename(columns={"cpcb_ground_naqi": "india_naqi"}, inplace=True)

        df_matched = pd.merge(df_predictors, cpcb_sub, on=["timestamp", "station_id"], how="inner")
        print(f"[Match] CPCB Ground Truth: {df_matched.shape[0]:,} matched rows")

        # 4. Attach OSM road infrastructure
        print(f"[OSM] Loading: {osm_path}")
        if osm_path.exists():
            with open(osm_path, "r", encoding="utf-8") as f:
                osm_data = json.load(f)

            df_matched["osm_total_roads"] = df_matched["station_id"].map(
                lambda sid: osm_data.get(sid, {}).get("total_road_segments", 0))
            df_matched["osm_major_highways"] = df_matched["station_id"].map(
                lambda sid: osm_data.get(sid, {}).get("major_highways_count", 0))
            df_matched["osm_secondary_roads"] = df_matched["station_id"].map(
                lambda sid: osm_data.get(sid, {}).get("secondary_roads_count", 0))
            df_matched["osm_road_density_km2"] = df_matched["station_id"].map(
                lambda sid: osm_data.get(sid, {}).get("road_density_per_sqkm", 0.0))
        else:
            print("[OSM] [WARN] Road network file not found -- setting defaults.")
            df_matched["osm_total_roads"] = 0
            df_matched["osm_major_highways"] = 0
            df_matched["osm_secondary_roads"] = 0
            df_matched["osm_road_density_km2"] = 0.0

        # 5. Compute spatial physics features
        print("[Physics] Computing Haversine distances, IDW weights, wind transport vectors...")
        df_final = SpatialDispersionPhysics.add_spatial_physics_features(df_matched)

        # Drop rows missing the target label
        df_final = df_final.dropna(subset=["india_naqi"]).reset_index(drop=True)
        df_final = df_final.sort_values(["timestamp", "station_id"]).reset_index(drop=True)

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_final.to_csv(output_path, index=False)

        print("\n" + "=" * 80)
        print(f"[STEP 03] [OK] Master Matrix: {df_final.shape[0]:,} rows x {df_final.shape[1]} cols")
        print(f"  Output: {output_path}")
        print(f"  Label:  'india_naqi' (Physical CPCB CAAQMS readings)")
        print(f"\n{df_final.groupby('station_id')['india_naqi'].describe()}")
        print("=" * 80)

        return df_final


if __name__ == "__main__":
    MasterMatrixMerger().merge()
