"""
Step 03: Spatial Clustering & Hotspot Identification Pipeline.
Implements:
1. Getis-Ord Gi* Local Spatial Autocorrelation to identify statistically significant
   HCHO and biomass burning hotspots (99%, 95%, 90% confidence levels).
2. Density-Based Spatial Clustering of Applications with Noise (DBSCAN) to delineate
   discrete geographic biomass burning emission plumes across India.
3. Exports GIS-ready GeoJSON layers and analytical summaries to ds/data/hotspots/.
"""

import json
import time
from typing import Tuple, List, Dict
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from scipy.spatial import cKDTree, ConvexHull
from sklearn.cluster import DBSCAN

DS_DIR = Path(__file__).resolve().parent
DATA_DIR = DS_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
HOTSPOTS_DIR = DATA_DIR / "hotspots"
HOTSPOTS_DIR.mkdir(parents=True, exist_ok=True)


def calculate_getis_ord_gi_star(df: pd.DataFrame, distance_threshold_deg: float = 1.2) -> pd.DataFrame:
    """
    Computes the Getis-Ord Gi* local spatial statistic for every grid cell across India.
    Identifies spatial clusters of high values (hotspots) and low values (coldspots).
    
    Formula:
      Gi* = (sum_j(w_ij * x_j) - X_bar * sum_j(w_ij)) / (S * sqrt((n * sum_j(w_ij^2) - (sum_j(w_ij))^2) / (n - 1)))
    """
    print(f"\n[1/3] Calculating Getis-Ord Gi* Spatial Autocorrelation (bandwidth = {distance_threshold_deg} deg)...")
    coords = df[["latitude", "longitude"]].values
    # Variable of interest: composite biomass burning index = HCHO concentration enhanced by FRP
    # x_i combines TROPOMI HCHO (molec/cm2) with fire intensity
    values = df["hcho_molec_cm2_e15"].values + (np.log1p(df["total_frp_mw"].values) * 0.45)
    
    n = len(values)
    x_bar = np.mean(values)
    s = np.std(values, ddof=1)
    
    # Build spatial KD-Tree for rapid spatial neighbor lookups
    tree = cKDTree(coords)
    
    # Query all neighbors within distance threshold (approx 130 km)
    neighbors_list = tree.query_ball_tree(tree, r=distance_threshold_deg)
    
    gi_z_scores = np.zeros(n, dtype=np.float64)
    p_values = np.ones(n, dtype=np.float64)
    
    for i in range(n):
        idxs = neighbors_list[i]
        # Distance-decay weights
        dists = np.sqrt(np.sum((coords[idxs] - coords[i])**2, axis=1))
        weights = np.exp(-dists / (distance_threshold_deg / 2.0))
        
        sum_w = np.sum(weights)
        sum_w_sq = np.sum(weights**2)
        sum_wx = np.sum(weights * values[idxs])
        
        numerator = sum_wx - (x_bar * sum_w)
        denominator = s * np.sqrt(((n * sum_w_sq) - (sum_w**2)) / (n - 1))
        
        if denominator > 0:
            z = numerator / denominator
            gi_z_scores[i] = z
        else:
            gi_z_scores[i] = 0.0

    df["gi_z_score"] = np.round(gi_z_scores, 3)

    # Classify into statistical significance bins
    def classify_significance(z):
        if z >= 2.58:
            return "Hotspot (99% Confidence, p < 0.01)"
        elif z >= 1.96:
            return "Hotspot (95% Confidence, p < 0.05)"
        elif z >= 1.65:
            return "Hotspot (90% Confidence, p < 0.10)"
        elif z <= -1.96:
            return "Coldspot (95% Confidence)"
        else:
            return "Not Statistically Significant"

    df["hotspot_category"] = df["gi_z_score"].apply(classify_significance)
    df["is_hotspot"] = df["gi_z_score"] >= 1.96

    hotspot_99 = (df["gi_z_score"] >= 2.58).sum()
    hotspot_95 = ((df["gi_z_score"] >= 1.96) & (df["gi_z_score"] < 2.58)).sum()
    hotspot_90 = ((df["gi_z_score"] >= 1.65) & (df["gi_z_score"] < 1.96)).sum()

    print(f"  -> Hotspots at 99% Confidence (Z >= 2.58): {hotspot_99:,} cells")
    print(f"  -> Hotspots at 95% Confidence (Z >= 1.96): {hotspot_95:,} cells")
    print(f"  -> Hotspots at 90% Confidence (Z >= 1.65): {hotspot_90:,} cells")
    return df


def perform_dbscan_clustering(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Applies DBSCAN clustering on significant HCHO/FRP hotspots to delineate
    continuous regional biomass burning plumes across India.
    """
    print("\n[2/3] Performing DBSCAN Spatial Density Clustering on Emission Hotspots...")
    
    # Filter candidate cells: must be significant Getis-Ord hotspot or have active fires
    candidates = df[
        (df["gi_z_score"] >= 1.65) |
        (df["fire_count"] > 1) |
        (df["hcho_molec_cm2_e15"] >= 5.5)
    ].copy()

    if len(candidates) == 0:
        candidates = df.sort_values(by="hcho_molec_cm2_e15", ascending=False).head(100).copy()

    # Convert coordinates to radians for haversine metric (eps = 55 km / 6371 km)
    coords_rad = np.radians(candidates[["latitude", "longitude"]].values)
    
    db = DBSCAN(eps=55.0 / 6371.0, min_samples=6, metric="haversine")
    candidates["raw_cluster_id"] = db.fit_predict(coords_rad)

    # Name and summarize major clusters based on geographical centroids
    raw_clusters = []
    
    ECO_CLUSTER_NAMES = {
        "north": "Punjab-Haryana Agrarian Stubble Burning Core (Indo-Gangetic Basin)",
        "central": "Central Deciduous Forest Fire Belt (Madhya Pradesh / Bundelkhand)",
        "east_igp": "Central-Eastern Forest Fire & Industrial Basin (Chhattisgarh / Odisha / Jharkhand)",
        "vidarbha": "Vidarbha & Northern Deccan Forest Fringe (Maharashtra / Telangana)",
        "northeast": "Northeast Highland Shifting Cultivation (Assam / Mizoram)",
        "peninsula": "Deccan Plateau & Western Ghats Fringe",
        "west_coast": "Western Coastal & Gujarat Agricultural Belt"
    }

    for c_id in sorted(candidates["raw_cluster_id"].unique()):
        if c_id == -1:
            continue  # Noise points
        
        c_subset = candidates[candidates["raw_cluster_id"] == c_id]
        if len(c_subset) < 8:
            continue  # Ignore tiny micro-clusters
            
        c_lat = float(c_subset["latitude"].mean())
        c_lon = float(c_subset["longitude"].mean())
        
        # Categorize region by centroid
        if c_lat >= 28.5 and c_lon <= 77.5:
            c_name = ECO_CLUSTER_NAMES["north"]
            region_tag = "North (Punjab/Haryana)"
        elif 21.0 <= c_lat <= 25.5 and 80.0 <= c_lon <= 88.5:
            c_name = ECO_CLUSTER_NAMES["east_igp"]
            region_tag = "Eastern Forest & Mineral Basin"
        elif 22.5 <= c_lat <= 28.5 and 74.5 <= c_lon <= 80.5:
            c_name = ECO_CLUSTER_NAMES["central"]
            region_tag = "Central India (MP/Bundelkhand)"
        elif 18.5 <= c_lat <= 22.5 and 76.0 <= c_lon <= 80.5:
            c_name = ECO_CLUSTER_NAMES["vidarbha"]
            region_tag = "Vidarbha & Northern Deccan"
        elif 20.0 <= c_lat <= 24.0 and 68.5 <= c_lon <= 74.0:
            c_name = ECO_CLUSTER_NAMES["west_coast"]
            region_tag = "Western Gujarat Belt"
        elif c_lon >= 89.0:
            c_name = ECO_CLUSTER_NAMES["northeast"]
            region_tag = "Northeast India"
        elif c_lat <= 18.0 and 75.0 <= c_lon <= 81.5:
            c_name = ECO_CLUSTER_NAMES["peninsula"]
            region_tag = "Deccan/Western Ghats"
        else:
            c_name = f"Regional Biomass Plume #{c_id + 1}"
            region_tag = "Regional Corridor"

        # Compute accurate boundary envelope via ConvexHull
        coords = c_subset[["longitude", "latitude"]].values
        if len(coords) >= 4:
            try:
                hull = ConvexHull(coords)
                poly_coords = coords[hull.vertices].tolist()
                poly_coords.append(poly_coords[0])  # Close ring
            except Exception:
                poly_coords = [
                    [float(c_subset["longitude"].min()), float(c_subset["latitude"].min())],
                    [float(c_subset["longitude"].max()), float(c_subset["latitude"].min())],
                    [float(c_subset["longitude"].max()), float(c_subset["latitude"].max())],
                    [float(c_subset["longitude"].min()), float(c_subset["latitude"].max())],
                    [float(c_subset["longitude"].min()), float(c_subset["latitude"].min())]
                ]
        else:
            poly_coords = [
                [float(c_subset["longitude"].min()), float(c_subset["latitude"].min())],
                [float(c_subset["longitude"].max()), float(c_subset["latitude"].min())],
                [float(c_subset["longitude"].max()), float(c_subset["latitude"].max())],
                [float(c_subset["longitude"].min()), float(c_subset["latitude"].max())],
                [float(c_subset["longitude"].min()), float(c_subset["latitude"].min())]
            ]

        summary = {
            "raw_id": int(c_id),
            "cluster_name": c_name,
            "region_tag": region_tag,
            "centroid": {"lat": round(c_lat, 4), "lon": round(c_lon, 4)},
            "bounds": {
                "min_lat": round(float(c_subset["latitude"].min()), 4),
                "max_lat": round(float(c_subset["latitude"].max()), 4),
                "min_lon": round(float(c_subset["longitude"].min()), 4),
                "max_lon": round(float(c_subset["longitude"].max()), 4)
            },
            "polygon_coords": poly_coords,
            "cell_count": int(len(c_subset)),
            "total_active_fires": int(c_subset["fire_count"].sum()),
            "total_frp_mw": round(float(c_subset["total_frp_mw"].sum()), 1),
            "mean_hcho_molec_cm2_e15": round(float(c_subset["hcho_molec_cm2_e15"].mean()), 2),
            "peak_hcho_molec_cm2_e15": round(float(c_subset["hcho_molec_cm2_e15"].max()), 2),
            "mean_gi_z_score": round(float(c_subset["gi_z_score"].mean()), 2),
            "dominant_wind_dir_deg": round(float(c_subset["era5_wind_dir_deg"].mean()), 1),
            "mean_wind_speed_ms": round(float(c_subset["era5_wind_speed_ms"].mean()), 2)
        }
        raw_clusters.append(summary)

    # Sort clusters by integrated fire radiative power
    raw_clusters.sort(key=lambda x: x["total_frp_mw"], reverse=True)

    # Re-assign clean sequential 1-based cluster IDs
    cluster_summaries = []
    id_mapping = {}
    for idx, c in enumerate(raw_clusters, start=1):
        c["cluster_id"] = idx
        id_mapping[c["raw_id"]] = idx
        cluster_summaries.append(c)

    print(f"  -> Identified {len(cluster_summaries)} Discrete Regional Biomass Emission Clusters:")
    for idx, c in enumerate(cluster_summaries[:5]):
        print(f"    Cluster #{c['cluster_id']}: {c['cluster_name']}")
        print(f"       Centroid: ({c['centroid']['lat']}, {c['centroid']['lon']}) | Fires: {c['total_active_fires']:,} | FRP: {c['total_frp_mw']:,.1f} MW | Mean HCHO: {c['mean_hcho_molec_cm2_e15']} x10^15")

    # Map cluster id back to original dataframe
    candidates["cluster_id"] = candidates["raw_cluster_id"].map(id_mapping).fillna(-1).astype(int)
    df = df.merge(candidates[["latitude", "longitude", "cluster_id"]], on=["latitude", "longitude"], how="left")
    df["cluster_id"] = df["cluster_id"].fillna(-1).astype(int)
    return df, cluster_summaries


def export_hotspot_geospatial_layers(df: pd.DataFrame, cluster_summaries: List[Dict]):
    """
    Exports clean, production GeoJSON layers for Leaflet map visualization:
    1. Getis-Ord Gi* Significant Hotspots Polygon/Point layer
    2. Discrete DBSCAN Cluster Envelopes
    3. Analytical Summary JSON
    """
    print("\n[3/3] Exporting Hotspot GeoJSON Layers & Summaries to ds/data/hotspots/...")
    
    # 1. Getis-Ord Hotspots GeoJSON (90%, 95%, 99% significance tiers)
    hotspot_cells = df[df["gi_z_score"] >= 1.65].copy()
    features = []

    for _, row in hotspot_cells.iterrows():
        z = float(row["gi_z_score"])
        conf_tier = "99%" if z >= 2.58 else ("95%" if z >= 1.96 else "90%")
        color = "#dc2626" if z >= 2.58 else ("#ea580c" if z >= 1.96 else "#f59e0b")

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(float(row["longitude"]), 4), round(float(row["latitude"]), 4)]
            },
            "properties": {
                "lat": round(float(row["latitude"]), 3),
                "lon": round(float(row["longitude"]), 3),
                "gi_z_score": round(z, 2),
                "confidence_tier": conf_tier,
                "color": color,
                "hcho_molec_cm2_e15": round(float(row["hcho_molec_cm2_e15"]), 2),
                "fire_count": int(row["fire_count"]),
                "frp_mw": round(float(row["total_frp_mw"]), 1),
                "cluster_id": int(row.get("cluster_id", -1)),
                "eco_zone": str(row.get("eco_zone", "India"))
            }
        })

    hotspot_geojson_path = HOTSPOTS_DIR / "hcho_hotspots_getis_ord.geojson"
    with open(hotspot_geojson_path, "w") as f:
        json.dump({
            "type": "FeatureCollection",
            "metadata": {
                "title": "Sentinel-5P HCHO Getis-Ord Gi* Hotspots (India)",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "hotspot_count": len(features),
                "thresholds": {"99_pct": 2.58, "95_pct": 1.96, "90_pct": 1.65}
            },
            "features": features
        }, f)
    print(f"  [OK] Exported Getis-Ord GeoJSON: {hotspot_geojson_path} ({len(features):,} hotspot cells)")

    # 2. DBSCAN Cluster Centroids & Envelopes GeoJSON
    cluster_features = []
    for c in cluster_summaries:
        b = c["bounds"]
        poly_coords = c.get("polygon_coords") or [
            [b["min_lon"], b["min_lat"]],
            [b["max_lon"], b["min_lat"]],
            [b["max_lon"], b["max_lat"]],
            [b["min_lon"], b["max_lat"]],
            [b["min_lon"], b["min_lat"]]
        ]

        # Export properties without internal raw fields
        props = {k: v for k, v in c.items() if k not in ("raw_id", "polygon_coords")}

        cluster_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [poly_coords]
            },
            "properties": props
        })

    cluster_geojson_path = HOTSPOTS_DIR / "biomass_clusters_dbscan.geojson"
    with open(cluster_geojson_path, "w") as f:
        json.dump({
            "type": "FeatureCollection",
            "metadata": {"cluster_count": len(cluster_summaries)},
            "features": cluster_features
        }, f)
    print(f"  [OK] Exported DBSCAN Clusters GeoJSON: {cluster_geojson_path}")

    # 3. Comprehensive Summary JSON for Backend Dashboard API
    summary_path = HOTSPOTS_DIR / "hotspots_summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "domain": "India (6.5N - 37.0N, 68.0E - 97.5E)",
            "metrics": {
                "total_grid_cells": len(df),
                "total_hotspots_99_pct": int((df["gi_z_score"] >= 2.58).sum()),
                "total_hotspots_95_pct": int((df["gi_z_score"] >= 1.96).sum()),
                "total_active_fires": int(df["fire_count"].sum()),
                "total_frp_mw": round(float(df["total_frp_mw"].sum()), 1),
                "mean_india_hcho_e15": round(float(df["hcho_molec_cm2_e15"].mean()), 2),
                "max_india_hcho_e15": round(float(df["hcho_molec_cm2_e15"].max()), 2),
                "distinct_clusters_count": len(cluster_summaries)
            },
            "top_clusters": cluster_summaries
        }, f, indent=2)
    print(f"  [OK] Exported Hotspots Summary JSON: {summary_path}")


def run_pipeline():
    print("=" * 80)
    print("DS STEP 03: SPATIO-TEMPORAL CLUSTERING & HOTSPOT GENERATION (INDIA)")
    print("=" * 80)
    start_t = time.time()

    csv_path = PROCESSED_DIR / "india_hcho_preprocessed_grid.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing {csv_path}. Run 02_preprocessing.py first.")

    df = pd.read_csv(csv_path)
    df_gi = calculate_getis_ord_gi_star(df)
    df_clustered, summaries = perform_dbscan_clustering(df_gi)
    export_hotspot_geospatial_layers(df_clustered, summaries)

    duration = time.time() - start_t
    print("\n" + "=" * 80)
    print(f"[SUCCESS] Spatial Hotspot Generation completed in {duration:.2f} seconds.")
    print("=" * 80)


if __name__ == "__main__":
    from typing import Tuple, List, Dict
    run_pipeline()
