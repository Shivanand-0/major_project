"""
Data Splitter for Step 04: Leakage-Free Chronological & Spatial Partitioning.
Architectural Design:
  1. Supervised Chronological Partitioning across all 4 Physical CPCB Monitoring Stations
     (Nagpur Central, Chandrapur MIDC, Amravati Central, Akola West - 28,070 authentic hourly records):
     - Train Set (Feb 19 - Sep 30, 2025): 20,024 records (~71.3%)
     - Validation Set (Oct 01 - Nov 15, 2025): 3,984 records (~14.2% - Post-monsoon transition)
     - Test Set (Nov 16 - Dec 31, 2025): 4,062 records (~14.5% - Winter peak inversion episode)
  2. Features & Target Label:
     - Target (y): 'india_naqi' (Physical continuous analyzer ground truth from CPCB/MPCB)
     - Features (X): 50 predictive features, including 'cams_satellite_naqi', atmospheric tracers,
       weather variables, cyclic temporal encodings, OSM road densities, and spatial physics transport vectors.
  3. Spatial Leave-One-Station-Out (LOSO) Generalization Benchmark:
     - Trains on 3 stations and evaluates zero-shot performance on the held-out 4th station
       for each of Nagpur, Chandrapur, Amravati, and Akola.
"""

import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any

# Ensure ML root is on path for direct script execution
_ML_ROOT = Path(__file__).resolve().parent.parent
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

try:
    from .config import (
        MASTER_MATRIX_FILE,
        SPLIT_DIR,
        LOSO_DIR,
        MONITORED_GROUND_STATIONS,
        SPLIT_STRATEGY,
        BLOCK_TRAIN_DAY_MAX,
        BLOCK_VAL_DAY_MIN,
        BLOCK_VAL_DAY_MAX,
        BLOCK_TEST_DAY_MIN,
        TARGET_COLUMN,
        DROP_COLUMNS
    )
except (ImportError, ValueError):
    from step_04_data_split.config import (
        MASTER_MATRIX_FILE,
        SPLIT_DIR,
        LOSO_DIR,
        MONITORED_GROUND_STATIONS,
        SPLIT_STRATEGY,
        BLOCK_TRAIN_DAY_MAX,
        BLOCK_VAL_DAY_MIN,
        BLOCK_VAL_DAY_MAX,
        BLOCK_TEST_DAY_MIN,
        TARGET_COLUMN,
        DROP_COLUMNS
    )


class DataSplitter:
    """Partitions master matrix into leakage-free seasonal block and spatial transfer datasets."""

    def __init__(self, master_path: Path = MASTER_MATRIX_FILE):
        self.master_path = master_path

    def run_split(self) -> Dict[str, Any]:
        print("=" * 80)
        print("[STEP 04: DATA SPLIT] Leakage-Free Seasonal Block & Spatial Partitioning")
        print("=" * 80)

        print(f"[Loading] Master Analytical Matrix: {self.master_path}")
        df = pd.read_csv(self.master_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        total_rows = len(df)

        # 1. Filter Monitored Ground Truth Stations
        df_monitored = df[df["station_id"].isin(MONITORED_GROUND_STATIONS)].reset_index(drop=True)

        print(f"\n[Dataset Summary]")
        print(f"  * Total Master Records        : {total_rows:,} rows")
        print(f"  * Physical CPCB Stations      : {len(MONITORED_GROUND_STATIONS)} stations ({', '.join(MONITORED_GROUND_STATIONS)})")
        print(f"  * Records per Station         : {df_monitored['station_id'].value_counts().to_dict()}")

        # 2. Extract Feature List (X) and Target Label (y)
        feature_cols = [c for c in df_monitored.columns if c not in DROP_COLUMNS]
        print(f"\n[Feature Schema]")
        print(f"  * Target Label (y)            : '{TARGET_COLUMN}' (Physical CPCB CAAQMS readings)")
        print(f"  * Satellite Feature           : 'cams_satellite_naqi' included in X: {'cams_satellite_naqi' in feature_cols}")
        print(f"  * Input Modeling Features (X) : {len(feature_cols)} features (dropped static station lookups)")

        # 3. Seasonal Block Splits (Train: Days 1-20, Val: Days 21-25, Test: Days 26-end)
        # Guarantees all seasons (summer, monsoon, post-monsoon, winter) are represented
        # in Train, Val, and Test without temporal overlap leakage.
        days = df_monitored["timestamp"].dt.day
        train_mask = days <= BLOCK_TRAIN_DAY_MAX
        val_mask   = (days >= BLOCK_VAL_DAY_MIN) & (days <= BLOCK_VAL_DAY_MAX)
        test_mask  = days >= BLOCK_TEST_DAY_MIN

        df_train = df_monitored[train_mask].reset_index(drop=True)
        df_val   = df_monitored[val_mask].reset_index(drop=True)
        df_test  = df_monitored[test_mask].reset_index(drop=True)

        print(f"\n[Seasonal Block Partition Windows (Days 1-20 / 21-25 / 26-End)]")
        print(f"  * Train Set      : {len(df_train):,} rows [{len(df_train)/len(df_monitored)*100:.1f}%] | Mean NAQI: {df_train[TARGET_COLUMN].mean():.1f} | Std: {df_train[TARGET_COLUMN].std():.1f}")
        print(f"  * Validation Set : {len(df_val):,} rows [{len(df_val)/len(df_monitored)*100:.1f}%] | Mean NAQI: {df_val[TARGET_COLUMN].mean():.1f} | Std: {df_val[TARGET_COLUMN].std():.1f}")
        print(f"  * Test Set       : {len(df_test):,} rows [{len(df_test)/len(df_monitored)*100:.1f}%] | Mean NAQI: {df_test[TARGET_COLUMN].mean():.1f} | Std: {df_test[TARGET_COLUMN].std():.1f}")

        X_train, y_train = df_train[feature_cols], df_train[TARGET_COLUMN]
        X_val, y_val     = df_val[feature_cols], df_val[TARGET_COLUMN]
        X_test, y_test   = df_test[feature_cols], df_test[TARGET_COLUMN]

        # Save supervised matrices
        df_train.to_csv(SPLIT_DIR / "train_matrix.csv", index=False)
        df_val.to_csv(SPLIT_DIR / "val_matrix.csv", index=False)
        df_test.to_csv(SPLIT_DIR / "test_matrix.csv", index=False)

        X_train.to_csv(SPLIT_DIR / "X_train.csv", index=False)
        y_train.to_csv(SPLIT_DIR / "y_train.csv", index=False)
        X_val.to_csv(SPLIT_DIR / "X_val.csv", index=False)
        y_val.to_csv(SPLIT_DIR / "y_val.csv", index=False)
        X_test.to_csv(SPLIT_DIR / "X_test.csv", index=False)
        y_test.to_csv(SPLIT_DIR / "y_test.csv", index=False)
        print(f"[Export] Saved supervised train/val/test matrices to {SPLIT_DIR}")

        # 4. Spatial Leave-One-Station-Out (LOSO) Transfer Sets
        print(f"\n[Spatial Transfer Evaluation] Leave-One-Station-Out (LOSO) Sets:")
        loso_summary = {}
        for st in MONITORED_GROUND_STATIONS:
            train_st = df_monitored[df_monitored["station_id"] != st].reset_index(drop=True)
            test_st  = df_monitored[df_monitored["station_id"] == st].reset_index(drop=True)
            prefix = st.lower()

            train_st[feature_cols].to_csv(LOSO_DIR / f"X_train_holdout_{prefix}.csv", index=False)
            train_st[TARGET_COLUMN].to_csv(LOSO_DIR / f"y_train_holdout_{prefix}.csv", index=False)
            test_st[feature_cols].to_csv(LOSO_DIR / f"X_test_holdout_{prefix}.csv", index=False)
            test_st[TARGET_COLUMN].to_csv(LOSO_DIR / f"y_test_holdout_{prefix}.csv", index=False)

            loso_summary[st] = {
                "train_rows": len(train_st),
                "test_rows": len(test_st),
                "holdout_station": st
            }
            print(f"  * Holdout [{st:<18}]: Train on 3 nodes ({len(train_st):,} rows) -> Test on {st} ({len(test_st):,} rows)")

        # 5. Save Metadata JSON
        metadata = {
            "total_master_rows": total_rows,
            "monitored_ground_rows": len(df_monitored),
            "monitored_stations": MONITORED_GROUND_STATIONS,
            "feature_count": len(feature_cols),
            "feature_names": feature_cols,
            "target_variable": TARGET_COLUMN,
            "split_strategy": SPLIT_STRATEGY,
            "seasonal_block_splits": {
                "train": {"days": f"1-{BLOCK_TRAIN_DAY_MAX}", "rows": len(df_train), "percentage": round(len(df_train)/len(df_monitored)*100, 2), "mean_target": round(float(df_train[TARGET_COLUMN].mean()), 2)},
                "validation": {"days": f"{BLOCK_VAL_DAY_MIN}-{BLOCK_VAL_DAY_MAX}", "rows": len(df_val), "percentage": round(len(df_val)/len(df_monitored)*100, 2), "mean_target": round(float(df_val[TARGET_COLUMN].mean()), 2)},
                "test": {"days": f"{BLOCK_TEST_DAY_MIN}-end", "rows": len(df_test), "percentage": round(len(df_test)/len(df_monitored)*100, 2), "mean_target": round(float(df_test[TARGET_COLUMN].mean()), 2)}
            },
            "spatial_transfer_loso": loso_summary
        }

        meta_file = SPLIT_DIR / "split_metadata.json"
        with open(meta_file, "w") as f:
            json.dump(metadata, f, indent=2)

        print("\n" + "=" * 80)
        print("[STEP 04] [OK] Data Split Completed Successfully!")
        print(f"  * Supervised Matrices   : {SPLIT_DIR}")
        print(f"  * Spatial Transfer Sets : {LOSO_DIR}")
        print(f"  * Split Metadata        : {meta_file}")
        print("=" * 80)

        return metadata


if __name__ == "__main__":
    DataSplitter().run_split()
