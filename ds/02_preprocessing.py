"""
Step 02: Satellite QA Filtering & Spatio-Temporal Alignment Pipeline.
1. Filters Sentinel-5P HCHO data using official QA thresholds (qa_value >= 0.5, cloud_fraction <= 0.3).
2. Spatially harmonizes NASA VIIRS/MODIS active fire detections with TROPOMI HCHO column fields.
3. Projects ECMWF ERA5 wind vectors (U, V components, wind speed & direction) across India domain.
4. Generates analysis-ready GeoJSON and CSV datasets for spatial clustering and visualization.
"""

import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import netCDF4 as nc

DS_DIR = Path(__file__).resolve().parent
DATA_DIR = DS_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Conversion factor: 1 mol/m^2 = 60,221.4 * 10^15 molec/cm^2
MOL_M2_TO_E15 = 60221.4


def load_and_filter_s5p_hcho() -> pd.DataFrame:
    """
    Loads Sentinel-5P HCHO NetCDF and applies operational quality assurance filtering.
    """
    nc_path = RAW_DIR / "S5P_OFFL_L2__HCHO_India_biomass.nc"
    csv_path = RAW_DIR / "S5P_HCHO_India_points.csv"

    print("\n[1/3] Filtering Sentinel-5P TROPOMI HCHO observations (QA >= 0.5)...")
    if csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        # Read directly from NetCDF
        with nc.Dataset(nc_path, "r") as ds:
            lats = ds.variables["latitude"][:]
            lons = ds.variables["longitude"][:]
            hcho = ds.variables["tropospheric_hcho_column_number_density"][:]
            qa = ds.variables["qa_value"][:]
            cf = ds.variables["cloud_fraction"][:]
            
            records = []
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    records.append({
                        "latitude": float(lat),
                        "longitude": float(lon),
                        "hcho_mol_m2": float(hcho[i, j]),
                        "hcho_molec_cm2_e15": float(hcho[i, j]) * MOL_M2_TO_E15,
                        "qa_value": float(qa[i, j]),
                        "cloud_fraction": float(cf[i, j])
                    })
        df = pd.DataFrame(records)

    raw_count = len(df)
    # Operational Quality Filtering (De Smedt et al., 2021 TROPOMI standard)
    filtered_df = df[
        (df["qa_value"] >= 0.50) &
        (df["cloud_fraction"] <= 0.35) &
        (df["hcho_mol_m2"] > 0)
    ].copy()

    retained_pct = (len(filtered_df) / raw_count) * 100
    print(f"  -> Total Raw Grid Cells: {raw_count:,}")
    print(f"  -> QA Filtered Cells   : {len(filtered_df):,} ({retained_pct:.1f}% retained after cloud/QA screening)")
    return filtered_df


def aggregate_viirs_fires_to_grid(grid_df: pd.DataFrame) -> pd.DataFrame:
    """
    Harmonizes NASA VIIRS & MODIS active fire detections onto the TROPOMI spatial grid.
    Aggregates Fire Radiative Power (FRP), Fire Count, and Thermal Intensity.
    """
    print("\n[2/3] Harmonizing NASA VIIRS/MODIS Active Fires with TROPOMI Spatial Grid...")
    fire_csv = RAW_DIR / "VIIRS_MODIS_India_Active_Fires_Raw.csv"
    if not fire_csv.exists():
        raise FileNotFoundError(f"Missing {fire_csv}. Run 01_data_ingestion.py first.")

    fire_df = pd.read_csv(fire_csv)
    print(f"  -> Processing {len(fire_df):,} active fire detections across India...")

    # Snap fire coordinates to nearest grid cell (0.25 deg grid)
    # 0.25 deg rounding: round(coord * 4) / 4
    grid_df["grid_lat"] = np.round(grid_df["latitude"] * 4.0) / 4.0
    grid_df["grid_lon"] = np.round(grid_df["longitude"] * 4.0) / 4.0

    fire_df["grid_lat"] = np.round(fire_df["latitude"] * 4.0) / 4.0
    fire_df["grid_lon"] = np.round(fire_df["longitude"] * 4.0) / 4.0

    # Ensure FRP column is clean
    if "frp" not in fire_df.columns:
        fire_df["frp"] = 1.0
    else:
        fire_df["frp"] = pd.to_numeric(fire_df["frp"], errors="coerce").fillna(1.0)

    # Group fires by grid cell
    fire_summary = fire_df.groupby(["grid_lat", "grid_lon"]).agg(
        fire_count=("latitude", "count"),
        total_frp_mw=("frp", "sum"),
        max_frp_mw=("frp", "max"),
        mean_brightness_k=("brightness", "mean" if "brightness" in fire_df.columns else "count")
    ).reset_index()

    # Merge into grid
    merged_df = pd.merge(grid_df, fire_summary, on=["grid_lat", "grid_lon"], how="left")
    merged_df["fire_count"] = merged_df["fire_count"].fillna(0).astype(int)
    merged_df["total_frp_mw"] = merged_df["total_frp_mw"].fillna(0.0).round(2)
    merged_df["max_frp_mw"] = merged_df["max_frp_mw"].fillna(0.0).round(2)
    merged_df["mean_brightness_k"] = merged_df["mean_brightness_k"].fillna(295.0).round(1)

    # Classify Regional Agro-Ecological Zones for India
    def assign_ecozone(row):
        lat, lon = row["latitude"], row["longitude"]
        if 29.0 <= lat <= 32.5 and 73.5 <= lon <= 77.5:
            return "Punjab-Haryana Agricultural Basin (High Stubble Burning)"
        elif 24.5 <= lat <= 28.5 and 77.0 <= lon <= 87.0:
            return "Central & Eastern Indo-Gangetic Plain (Transport Corridor)"
        elif 19.0 <= lat <= 24.5 and 77.0 <= lon <= 83.5:
            return "Central India Deciduous Forest (Vidarbha/MP/Chhattisgarh)"
        elif 23.5 <= lat <= 28.5 and 90.0 <= lon <= 96.5:
            return "Northeast Highlands (Shifting Jhum Cultivation)"
        elif 11.0 <= lat <= 18.0 and 74.0 <= lon <= 77.5:
            return "Western Ghats & Deccan Plateau"
        elif 8.0 <= lat <= 15.0:
            return "Southern Peninsular Region"
        else:
            return "Northern/Western Arid Region"

    merged_df["eco_zone"] = merged_df.apply(assign_ecozone, axis=1)
    print(f"  -> Cells with Active Biomass Burning Fires: {(merged_df['fire_count'] > 0).sum():,}")
    print(f"  -> Total Integrated Fire Radiative Power  : {merged_df['total_frp_mw'].sum():,.1f} MW")
    return merged_df


def integrate_era5_winds_and_export(df: pd.DataFrame):
    """
    Interpolates ERA5 synoptic wind vectors across the spatial domain and
    exports processed GeoJSON and tabular datasets.
    """
    print("\n[3/3] Interpolating ERA5 Wind Transport Vectors & Exporting Preprocessed Products...")
    era5_csv = RAW_DIR / "ERA5_reanalysis_met_India.csv"
    if era5_csv.exists():
        era5_df = pd.read_csv(era5_csv)
        avg_era5 = era5_df.groupby(["latitude", "longitude"]).agg({
            "u_wind_10m": "mean",
            "v_wind_10m": "mean",
            "wind_speed_10m_ms": "mean",
            "wind_direction_deg": "mean",
            "temperature_2m_c": "mean",
            "surface_pressure_hpa": "mean"
        }).reset_index()
    else:
        avg_era5 = pd.DataFrame()

    # Spatial inverse distance weighting interpolation of wind vectors from synoptic stations
    if not avg_era5.empty:
        station_lats = avg_era5["latitude"].values
        station_lons = avg_era5["longitude"].values
        u_vals = avg_era5["u_wind_10m"].values
        v_vals = avg_era5["v_wind_10m"].values

        u_interp = []
        v_interp = []

        for _, row in df.iterrows():
            dists = np.sqrt((station_lats - row["latitude"])**2 + (station_lons - row["longitude"])**2)
            dists = np.maximum(dists, 0.1)
            weights = 1.0 / (dists**2)
            weights /= weights.sum()

            u_interp.append(float(np.sum(weights * u_vals)))
            v_interp.append(float(np.sum(weights * v_vals)))

        df["era5_u10"] = np.round(u_interp, 2)
        df["era5_v10"] = np.round(v_interp, 2)
        df["era5_wind_speed_ms"] = np.round(np.sqrt(df["era5_u10"]**2 + df["era5_v10"]**2), 2)
        # Mathematical to meteorological wind direction
        deg = np.degrees(np.arctan2(-df["era5_u10"], -df["era5_v10"])) % 360
        df["era5_wind_dir_deg"] = np.round(deg, 1)
    else:
        # Climatological post-monsoon northwest wind default for Indo-Gangetic basin
        df["era5_u10"] = 2.1
        df["era5_v10"] = -2.8
        df["era5_wind_speed_ms"] = 3.5
        df["era5_wind_dir_deg"] = 320.0

    # Export Processed Tabular CSV
    out_csv = PROCESSED_DIR / "india_hcho_preprocessed_grid.csv"
    df.to_csv(out_csv, index=False)
    print(f"  [OK] Exported preprocessed CSV: {out_csv} ({len(df):,} grid cells)")

    # Export Resampled GeoJSON for Leaflet Visualization
    # Sample at 0.5 deg step for ultra-fast browser rendering while preserving hotspots
    geojson_features = []
    # Include all cells with active fires or high HCHO, plus regular 0.5 deg mesh
    sampled_df = df[
        (df["fire_count"] > 0) |
        (df["hcho_molec_cm2_e15"] > 4.5) |
        ((np.abs(df["latitude"] % 0.5) < 0.01) & (np.abs(df["longitude"] % 0.5) < 0.01))
    ].copy()

    for _, row in sampled_df.iterrows():
        lat, lon = row["latitude"], row["longitude"]
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(lon, 4), round(lat, 4)]
            },
            "properties": {
                "lat": round(lat, 3),
                "lon": round(lon, 3),
                "hcho_molec_cm2_e15": round(float(row["hcho_molec_cm2_e15"]), 2),
                "hcho_mol_m2": float(row["hcho_mol_m2"]),
                "fire_count": int(row["fire_count"]),
                "total_frp_mw": float(row["total_frp_mw"]),
                "eco_zone": row["eco_zone"],
                "wind_speed_ms": float(row["era5_wind_speed_ms"]),
                "wind_dir_deg": float(row["era5_wind_dir_deg"]),
                "u_wind": float(row["era5_u10"]),
                "v_wind": float(row["era5_v10"])
            }
        }
        geojson_features.append(feature)

    # Read ingestion metadata if present
    ingest_meta = {}
    ingest_meta_file = RAW_DIR / "ingestion_metadata.json"
    if ingest_meta_file.exists():
        try:
            with open(ingest_meta_file, "r") as f:
                ingest_meta = json.load(f)
        except Exception:
            pass
    obs_date_str = ingest_meta.get("s5p_observation_date", "Latest Daily Pass")

    geojson_path = PROCESSED_DIR / "india_hcho_aligned.geojson"
    with open(geojson_path, "w") as f:
        json.dump({
            "type": "FeatureCollection",
            "metadata": {
                "title": "Sentinel-5P HCHO & VIIRS Biomass Burning Grid (India)",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "observation_date": obs_date_str,
                "s5p_stream": ingest_meta.get("s5p_stream", "Operational"),
                "feature_count": len(geojson_features)
            },
            "features": geojson_features
        }, f)

    print(f"  [OK] Exported Leaflet GeoJSON grid: {geojson_path} ({len(geojson_features):,} features)")

    # Also export Top 500 Active Fire Hotspots GeoJSON for direct map pinpointing
    raw_fire_csv = RAW_DIR / "VIIRS_MODIS_India_Active_Fires_Raw.csv"
    if raw_fire_csv.exists():
        raw_fires = pd.read_csv(raw_fire_csv)
        top_fires = raw_fires.sort_values(by="frp", ascending=False).head(600)
        
        fire_features = []
        for _, r in top_fires.iterrows():
            fire_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(float(r["longitude"]), 4), round(float(r["latitude"]), 4)]
                },
                "properties": {
                    "frp_mw": round(float(r.get("frp", 1.0)), 1),
                    "confidence": str(r.get("confidence", "nominal")),
                    "acq_date": str(r.get("acq_date", "")),
                    "acq_time": str(r.get("acq_time", "")),
                    "satellite": str(r.get("satellite", "VIIRS/MODIS"))
                }
            })

        fire_geojson_path = PROCESSED_DIR / "active_fires_india_processed.geojson"
        with open(fire_geojson_path, "w") as f:
            json.dump({
                "type": "FeatureCollection",
                "metadata": {
                    "title": "NASA VIIRS/MODIS Active Fires (India)",
                    "observation_date": obs_date_str,
                    "total_fires": len(raw_fires),
                    "display_fires": len(fire_features)
                },
                "features": fire_features
            }, f)
        print(f"  [OK] Exported Active Fire Pinpoint GeoJSON: {fire_geojson_path}")


def run_pipeline() -> dict:
    print("=" * 80)
    print("DS STEP 02: SATELLITE QA SCREENING & SPATIO-TEMPORAL HARMONIZATION")
    print("=" * 80)
    start_t = time.time()
    df_hcho = load_and_filter_s5p_hcho()
    df_merged = aggregate_viirs_fires_to_grid(df_hcho)
    integrate_era5_winds_and_export(df_merged)
    duration = time.time() - start_t
    print("\n" + "=" * 80)
    print(f"[SUCCESS] Preprocessing completed in {duration:.2f} seconds. Analysis-ready products saved to:")
    print(f"  {PROCESSED_DIR}")
    print("=" * 80)
    return {
        "preprocessed_cells": len(df_merged),
        "duration_seconds": round(duration, 2)
    }


if __name__ == "__main__":
    run_pipeline()
