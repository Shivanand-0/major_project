"""
Unified Data Preprocessing Module for Step 02.
Cleans and transforms raw datasets from Step 01:
  1. Weather (ERA5)   → interpolation, wind vectors, dew point spread, cyclic time
  2. CAMS Satellite    → interpolation, combustion tracer ratio
  3. CPCB Ground Truth → interpolation, timestamp alignment

All cleaning logic in one place — no year-specific duplicate files.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Ensure ML root is on path for direct script execution
_ML_ROOT = Path(__file__).resolve().parent.parent
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

from step_01_raw_ingestion.config import (
    WEATHER_RAW_COMBINED,
    CAMS_RAW_COMBINED,
    CPCB_RAW_COMBINED,
    WEATHER_CLEAN_FILE,
    CAMS_CLEAN_FILE,
    CPCB_CLEAN_FILE,
)


class DataCleaner:
    """Preprocesses raw meteorological, satellite, and ground sensor datasets for ML training."""

    # ── Shared Helpers ──────────────────────────────────────

    @staticmethod
    def _interpolate_numeric(df: pd.DataFrame, exclude_cols: list = None) -> pd.DataFrame:
        """Per-station linear interpolation + bfill/ffill for numeric columns."""
        exclude = set(exclude_cols or [])
        numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c not in exclude]
        df[numeric_cols] = df.groupby("station_id")[numeric_cols].transform(
            lambda g: g.interpolate(method="linear").bfill().ffill()
        )
        return df

    @staticmethod
    def add_cyclic_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes continuous trigonometric cyclical encodings:
          - 24-hour diurnal cycle (sin/cos hour)
          - 7-day weekly cycle (sin/cos day-of-week)
          - 12-month seasonal cycle (sin/cos month)
          - Weekend binary indicator
        """
        df = df.copy()
        ts = pd.to_datetime(df["timestamp"])

        hour = ts.dt.hour.values
        dow = ts.dt.dayofweek.values
        month = ts.dt.month.values

        df["sin_hour"] = np.round(np.sin(2 * np.pi * hour / 24.0), 4)
        df["cos_hour"] = np.round(np.cos(2 * np.pi * hour / 24.0), 4)
        df["sin_dayofweek"] = np.round(np.sin(2 * np.pi * dow / 7.0), 4)
        df["cos_dayofweek"] = np.round(np.cos(2 * np.pi * dow / 7.0), 4)
        df["sin_month"] = np.round(np.sin(2 * np.pi * month / 12.0), 4)
        df["cos_month"] = np.round(np.cos(2 * np.pi * month / 12.0), 4)
        df["is_weekend"] = (dow >= 5).astype(int)

        return df

    # ── Individual Dataset Cleaners ──────────────────────

    def clean_weather(self, raw_path: Path = WEATHER_RAW_COMBINED) -> pd.DataFrame:
        """
        Cleans ERA5 weather dataset:
          - Timestamp normalization (strip timezone)
          - Linear interpolation of missing values
          - Dew point spread derivation
          - Wind vector decomposition (U, V components)
          - Cyclic temporal features
        """
        print(f"[Clean Weather] Loading: {raw_path}")
        df = pd.read_csv(raw_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
        df = df.sort_values(["station_id", "timestamp"]).reset_index(drop=True)

        df = self._interpolate_numeric(df)

        # Dew point spread
        if "temperature_2m" in df.columns and "dew_point_2m" in df.columns:
            df["dew_point_spread"] = (df["temperature_2m"] - df["dew_point_2m"]).clip(lower=0.0).round(2)

        # Wind vector decomposition
        if "wind_speed_10m" in df.columns and "wind_direction_10m" in df.columns:
            rad = np.radians(df["wind_direction_10m"])
            df["wind_u"] = np.round(-df["wind_speed_10m"] * np.sin(rad), 3)
            df["wind_v"] = np.round(-df["wind_speed_10m"] * np.cos(rad), 3)

        df = self.add_cyclic_temporal_features(df)

        df.to_csv(WEATHER_CLEAN_FILE, index=False)
        print(f"[Clean Weather] [OK] {len(df):,} rows -> {WEATHER_CLEAN_FILE}")
        return df

    def clean_cams_satellite(self, raw_path: Path = CAMS_RAW_COMBINED) -> pd.DataFrame:
        """
        Cleans CAMS satellite atmospheric chemistry:
          - Timestamp normalization
          - Linear interpolation
          - Combustion tracer ratio (NO2 / CO)
        """
        print(f"[Clean CAMS] Loading: {raw_path}")
        df = pd.read_csv(raw_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
        df = df.sort_values(["station_id", "timestamp"]).reset_index(drop=True)

        df = self._interpolate_numeric(df)

        if "nitrogen_dioxide" in df.columns and "carbon_monoxide" in df.columns:
            df["combustion_tracer_ratio"] = np.round(
                df["nitrogen_dioxide"] / (df["carbon_monoxide"] + 1e-4), 5
            )

        df.to_csv(CAMS_CLEAN_FILE, index=False)
        print(f"[Clean CAMS] [OK] {len(df):,} rows -> {CAMS_CLEAN_FILE}")
        return df

    def clean_cpcb_ground(self, raw_path: Path = CPCB_RAW_COMBINED) -> pd.DataFrame:
        """
        Cleans physical CPCB ground truth measurements:
          - Timestamp normalization (strip timezone for alignment)
          - Linear interpolation of sensor dropouts
        """
        print(f"[Clean CPCB] Loading: {raw_path}")
        df = pd.read_csv(raw_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
        df = df.sort_values(["station_id", "timestamp"]).reset_index(drop=True)

        df = self._interpolate_numeric(df, exclude_cols=["latitude", "longitude", "year"])

        df.to_csv(CPCB_CLEAN_FILE, index=False)
        print(f"[Clean CPCB] [OK] {len(df):,} rows -> {CPCB_CLEAN_FILE}")
        return df

    # ── Full Pipeline Runner ─────────────────────────────

    def run_all(self):
        """Executes full Step 02 preprocessing on all datasets."""
        print("=" * 80)
        print("STEP 02: DATA PREPROCESSING")
        print("=" * 80)
        self.clean_weather()
        self.clean_cams_satellite()
        self.clean_cpcb_ground()
        print("=" * 80)
        print("[STEP 02] [OK] All clean datasets exported to data/clean/")
        print("=" * 80)


if __name__ == "__main__":
    DataCleaner().run_all()
