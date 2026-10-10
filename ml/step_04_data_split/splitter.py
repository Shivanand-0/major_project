"""
Data Splitter for Step 04: Leakage-Free Chronological & Spatial Partitioning.
Architectural Design:
  1. Supervised Training: Exclusively on Ground-Truth Monitored Stations (Nagpur & Chandrapur)
     - 17,520 rows of authentic CPCB-monitored data.
     - Chronological train/val/test splits (Jan-Aug / Sep-Oct / Nov-Dec).
  2. Unmonitored Target Partition: (Amravati & Akola)
     - 17,520 rows of feature vectors (X) for Virtual Sensor deployment & mapping.
  3. Spatial Cross-Station Transfer (LOSO):
     - Train on Nagpur -> Evaluate on Chandrapur (and vice versa) to prove cross-city generalization.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any

try:
    from .config import (
        MASTER_MATRIX_FILE,
        SPLIT_DIR,
        LOSO_DIR,
        UNMONITORED_DIR,
        MONITORED_GROUND_STATIONS,
        UNMONITORED_TARGET_STATIONS,
        TRAIN_START,
        TRAIN_END,
        VAL_START,
        VAL_END,
        TEST_START,
        TEST_END,
        TARGET_COLUMN,
        DROP_COLUMNS
    )
except ImportError:
    from config import (
        MASTER_MATRIX_FILE,
        SPLIT_DIR,
        LOSO_DIR,
        UNMONITORED_DIR,
        MONITORED_GROUND_STATIONS,
        UNMONITORED_TARGET_STATIONS,
        TRAIN_START,
        TRAIN_END,
        VAL_START,
        VAL_END,
        TEST_START,
        TEST_END,
        TARGET_COLUMN,
        DROP_COLUMNS
    )


class DataSplitter:
    """Partitions master matrix into supervised training sets and unmonitored virtual sensor sets."""

    def __init__(self, master_path: Path = MASTER_MATRIX_FILE):
        self.master_path = master_path

    def run_split(self) -> Dict[str, Any]:
        print("=" * 80)
        print("[STEP 04: DATA SPLIT] Supervised Ground Partition & Virtual Target Separation")
        print("=" * 80)

        print(f"[Loading] Master Analytical Matrix: {self.master_path}")
        df = pd.read_csv(self.master_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        total_rows = len(df)

        # 1. Separate Monitored Ground Truth from Unmonitored Virtual Nodes
        df_monitored = df[df["station_id"].isin(MONITORED_GROUND_STATIONS)].reset_index(drop=True)
        df_unmonitored = df[df["station_id"].isin(UNMONITORED_TARGET_STATIONS)].reset_index(drop=True)

        print(f"\n[Partition Summary]")
        print(f"  • Monitored Stations (Ground Truth Training)  : {len(df_monitored):,} rows {MONITORED_GROUND_STATIONS}")
        print(f"  • Unmonitored Nodes (Virtual Sensor Deployment): {len(df_unmonitored):,} rows {UNMONITORED_TARGET_STATIONS}")

        # 2. Extract Feature List (X) and Target (y)
        feature_cols = [c for c in df.columns if c not in DROP_COLUMNS]
        print(f"[Features] Total Input Modeling Features (X): {len(feature_cols)}")
        print(f"[Target]   Primary Modeling Label (y)        : '{TARGET_COLUMN}'")

        # 3. Chronological Splits on Monitored Ground Truth
        train_mask = (df_monitored["timestamp"] >= TRAIN_START) & (df_monitored["timestamp"] <= TRAIN_END)
        val_mask   = (df_monitored["timestamp"] >= VAL_START) & (df_monitored["timestamp"] <= VAL_END)
        test_mask  = (df_monitored["timestamp"] >= TEST_START) & (df_monitored["timestamp"] <= TEST_END)

        df_train = df_monitored[train_mask].reset_index(drop=True)
        df_val   = df_monitored[val_mask].reset_index(drop=True)
        df_test  = df_monitored[test_mask].reset_index(drop=True)

        print(f"\n[Supervised Chronological Windows]")
        print(f"  • Train Set      : {len(df_train):,} rows ({TRAIN_START[:10]} to {TRAIN_END[:10]}) [{len(df_train)/len(df_monitored)*100:.1f}%]")
        print(f"  • Validation Set : {len(df_val):,} rows ({VAL_START[:10]} to {VAL_END[:10]}) [{len(df_val)/len(df_monitored)*100:.1f}%]")
        print(f"  • Out-of-Sample  : {len(df_test):,} rows ({TEST_START[:10]} to {TEST_END[:10]}) [{len(df_test)/len(df_monitored)*100:.1f}%]")

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

        # 4. Save Unmonitored Virtual Sensor Deployment Sets
        print(f"\n[Exporting Unmonitored Virtual Target Sets]")
        df_unmonitored.to_csv(UNMONITORED_DIR / "unmonitored_deployment_matrix.csv", index=False)
        df_unmonitored[feature_cols].to_csv(UNMONITORED_DIR / "X_unmonitored_all.csv", index=False)

        for unmonitored_st in UNMONITORED_TARGET_STATIONS:
            subset = df_unmonitored[df_unmonitored["station_id"] == unmonitored_st].reset_index(drop=True)
            prefix = unmonitored_st.lower()
            subset[feature_cols].to_csv(UNMONITORED_DIR / f"X_unmonitored_{prefix}.csv", index=False)
            print(f"  • Saved deployment features for {unmonitored_st:<18}: {len(subset):,} rows -> X_unmonitored_{prefix}.csv")

        # 5. Cross-Station Spatial Transfer (LOSO) between Monitored Stations
        print(f"\n[Spatial Transfer Evaluation] Cross-Station Holdouts (Nagpur <-> Chandrapur)")
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
            print(f"  • Train on {MONITORED_GROUND_STATIONS[1 if st==MONITORED_GROUND_STATIONS[0] else 0]} ({len(train_st):,} rows) -> Evaluate on {st} ({len(test_st):,} rows)")

        # 6. Save Metadata JSON
        metadata = {
            "total_master_rows": total_rows,
            "monitored_ground_rows": len(df_monitored),
            "unmonitored_deployment_rows": len(df_unmonitored),
            "monitored_stations": MONITORED_GROUND_STATIONS,
            "unmonitored_stations": UNMONITORED_TARGET_STATIONS,
            "feature_count": len(feature_cols),
            "feature_names": feature_cols,
            "target_variable": TARGET_COLUMN,
            "chronological_splits": {
                "train": {"start": TRAIN_START, "end": TRAIN_END, "rows": len(df_train), "percentage": round(len(df_train)/len(df_monitored)*100, 2)},
                "validation": {"start": VAL_START, "end": VAL_END, "rows": len(df_val), "percentage": round(len(df_val)/len(df_monitored)*100, 2)},
                "test": {"start": TEST_START, "end": TEST_END, "rows": len(df_test), "percentage": round(len(df_test)/len(df_monitored)*100, 2)}
            },
            "spatial_transfer_loso": loso_summary
        }

        meta_file = SPLIT_DIR / "split_metadata.json"
        with open(meta_file, "w") as f:
            json.dump(metadata, f, indent=2)

        print("\n" + "=" * 80)
        print("[SUCCESS] Data Split Completed with 100% Scientific Rigor!")
        print(f"[DIR] Supervised Matrices   : {SPLIT_DIR}")
        print(f"[DIR] Unmonitored Targets   : {UNMONITORED_DIR}")
        print(f"[DIR] Spatial Transfer Sets : {LOSO_DIR}")
        print(f"[METADATA] Summary File     : {meta_file}")
        print("=" * 80)

        return metadata


if __name__ == "__main__":
    splitter = DataSplitter()
    splitter.run_split()
